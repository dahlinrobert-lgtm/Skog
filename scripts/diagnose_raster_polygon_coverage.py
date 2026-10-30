#!/usr/bin/env python3
"""Compare original volume-raster coverage/value masks with harvested polygons."""
from __future__ import annotations
import argparse, json, tempfile, zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds
from rasterio.features import geometry_mask
from pyproj import CRS, Transformer
from shapely.geometry import shape, box, mapping
from shapely.ops import transform as transform_geometry

NODATA_FALLBACK = -1

def extract_tif(archive_path, target_dir):
    with zipfile.ZipFile(archive_path) as z:
        members=[m for m in z.infolist() if not m.is_dir() and Path(m.filename).suffix.lower() in {'.tif','.tiff'}]
        if len(members)!=1: raise ValueError(f'{archive_path.name}: expected one TIFF, found {len(members)}')
        p=target_dir/Path(members[0].filename).name
        with z.open(members[0]) as src,p.open('wb') as dst:
            while chunk:=src.read(1024*1024): dst.write(chunk)
        return p

def inspect_raster(ds):
    nodata=ds.nodata if ds.nodata is not None else NODATA_FALLBACK
    counts=Counter(); total=0; minv=None; maxv=None; samples=[]
    block_h=512; block_w=1024
    for r in range(0,ds.height,block_h):
      for c in range(0,ds.width,block_w):
        a=ds.read(1,window=Window(c,r,min(block_w,ds.width-c),min(block_h,ds.height-r)),masked=False)
        total+=a.size
        counts['equal_nodata']+=int(np.count_nonzero(a==nodata))
        counts['zero']+=int(np.count_nonzero(a==0))
        counts['positive']+=int(np.count_nonzero(a>0))
        counts['negative_other']+=int(np.count_nonzero((a<0)&(a!=nodata)))
        v=a[a!=nodata]
        if v.size:
          lo,hi=int(v.min()),int(v.max()); minv=lo if minv is None else min(minv,lo); maxv=hi if maxv is None else max(maxv,hi)
          if len(samples)<100000:
            stride=max(1,v.size//max(1,100000-len(samples)))
            samples.extend(v[::stride][:100000-len(samples)].astype('int64').tolist())
    valid_samples=np.asarray(samples,dtype='int64')
    hist=Counter(valid_samples.tolist())
    return {'width':ds.width,'height':ds.height,'band_count':ds.count,'crs':ds.crs.to_string() if ds.crs else None,
      'bounds':{'left':ds.bounds.left,'bottom':ds.bounds.bottom,'right':ds.bounds.right,'top':ds.bounds.top},
      'resolution':list(ds.res),'transform':list(ds.transform),'dtype':ds.dtypes[0],'nodata':ds.nodata,
      'nodata_fallback_used':ds.nodata is None,'effective_nodata_test_value':nodata,'scale':list(ds.scales),'offset':list(ds.offsets),
      'units':list(ds.units),'descriptions':list(ds.descriptions),'band_tags':ds.tags(1),'dataset_tags':ds.tags(),
      'mask_flags':[str(x) for x in ds.mask_flag_enums[0]],'pixels_total':total,
      'pixels_equal_nodata':counts['equal_nodata'],'pixels_zero':counts['zero'],'pixels_positive':counts['positive'],
      'pixels_other_negative':counts['negative_other'],'pixels_valid':total-counts['equal_nodata'],
      'valid_min_sampled':minv,'valid_max_sampled':maxv,'sampled_value_frequency':dict(hist.most_common(30)),
      'sample_size_for_frequency':len(valid_samples)}

def inspect_polygons(ds, path):
    doc=json.loads(path.read_text(encoding='utf-8')); crsdoc=doc.get('crs')
    src_crs=CRS.from_user_input(crsdoc.get('properties',{}).get('name')) if crsdoc else CRS.from_epsg(4326)
    trans=Transformer.from_crs(src_crs,ds.crs,always_xy=True).transform
    extent=box(*ds.bounds); rows=[]
    for i,f in enumerate(doc.get('features',[])):
      if not f.get('geometry'): continue
      g=transform_geometry(trans,shape(f['geometry'])); inter=g.intersection(extent)
      row={'feature_id':str(f.get('id',(f.get('properties') or {}).get('OBJECTID',i))),
           'objectid':(f.get('properties') or {}).get('OBJECTID'),'kommun':(f.get('properties') or {}).get('Kommun'),
           'polygon_bounds_raster_crs':list(g.bounds),'intersects_raster_extent':bool(g.intersects(extent)),
           'intersection_area_m2':round(inter.area,2) if not inter.is_empty else 0}
      if inter.is_empty:
        row.update({'cells_inside_polygon':0,'valid_cells':0,'nodata_cells':0,'coverage_pct':0,'status':'outside_raster_extent'})
      else:
        raw=from_bounds(*inter.bounds,transform=ds.transform).round_offsets().round_lengths()
        c0=max(0,int(raw.col_off)); r0=max(0,int(raw.row_off)); c1=min(ds.width,int(raw.col_off+raw.width)); r1=min(ds.height,int(raw.row_off+raw.height))
        if c1<=c0 or r1<=r0:
          row.update({'cells_inside_polygon':0,'valid_cells':0,'nodata_cells':0,'coverage_pct':0,'status':'no_raster_cells_in_extent'})
        else:
          win=Window(c0,r0,c1-c0,r1-r0); arr=ds.read(1,window=win,masked=False)
          inside=geometry_mask([mapping(inter)],out_shape=arr.shape,transform=ds.window_transform(win),invert=True,all_touched=False)
          cells=int(inside.sum()); valid=int(np.count_nonzero(inside & (arr != (ds.nodata if ds.nodata is not None else NODATA_FALLBACK))))
          row.update({'cells_inside_polygon':cells,'valid_cells':valid,'nodata_cells':cells-valid,'coverage_pct':round(100*valid/max(1,cells),2),'status':'ok' if valid else 'no_valid_cells'})
      rows.append(row)
    return {'polygon_source_crs':src_crs.to_string(),'polygon_count':len(rows),'polygons':rows,
      'aggregate_cells_inside_polygons':sum(x['cells_inside_polygon'] for x in rows),
      'aggregate_valid_cells':sum(x['valid_cells'] for x in rows),
      'aggregate_nodata_cells':sum(x['nodata_cells'] for x in rows),
      'outside_extent_count':sum(x['status']=='outside_raster_extent' for x in rows)}

def main():
 p=argparse.ArgumentParser();p.add_argument('--raster',required=True,type=Path);p.add_argument('--polygon',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
 with tempfile.TemporaryDirectory(prefix='skog-raster-diagnostic-') as tmp:
  tif=extract_tif(a.raster,Path(tmp))
  with rasterio.open(tif) as ds:
   report={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'archive':a.raster.name,'tiff_member':tif.name,
    'raster':inspect_raster(ds),'polygon_comparison':inspect_polygons(ds,a.polygon),
    'interpretation_notes':['Full-raster value counts are exact for equality with the effective NoData value.','Sampled value frequency is a bounded sample, not a complete histogram.','Polygon masks use the raster native grid and pixel-centre inclusion (all_touched=False).','The diagnostic does not change or publish any raster-derived polygon values.']}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 r=report['raster'];q=report['polygon_comparison']
 print(f"RASTER_DIAGNOSTIC archive={a.raster.name} size={r['width']}x{r['height']} bounds={r['bounds']} nodata={r['effective_nodata_test_value']} valid_pixels={r['pixels_valid']} min={r['valid_min_sampled']} max={r['valid_max_sampled']}",flush=True)
 print(f"POLYGON_DIAGNOSTIC polygons={q['polygon_count']} outside_extent={q['outside_extent_count']} cells={q['aggregate_cells_inside_polygons']} valid={q['aggregate_valid_cells']} nodata={q['aggregate_nodata_cells']}",flush=True)
if __name__=='__main__': main()

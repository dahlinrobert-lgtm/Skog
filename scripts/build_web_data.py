from pathlib import Path
import json
from shapely.geometry import shape, mapping
ROOT=Path(__file__).resolve().parents[1]
src=ROOT/'data/latest.json'
out=ROOT/'data/latest_web.json'
data=json.loads(src.read_text(encoding='utf-8'))
features=data.get('cutting_notifications',{}).get('features',[])
for feature in features:
    geometry=feature.get('geometry')
    if geometry:
        try:
            feature['geometry']=mapping(shape(geometry).simplify(0.00003,preserve_topology=True))
        except Exception:
            pass
out.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print(f'Wrote {len(features)} features to {out}')

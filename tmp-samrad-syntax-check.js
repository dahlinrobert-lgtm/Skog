(function(){
"use strict";
let CENTER=[63.74646,19.66455], RADIUS=10000;
let searchCircle=null;
const PLANNED="https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaAvverkningsanmalan/MapServer/0/query";
const PERFORMED="https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaUtfordavverkning/MapServer/1/query";
const SAMRAD_POINTS="https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaSamrad/MapServer/0/query";
const SAMRAD_LINES="https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaSamrad/MapServer/1/query";
const SAMRAD_AREAS="https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaSamrad/MapServer/2/query";
const map=L.map("map",{preferCanvas:true}).setView(CENTER,11);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(map);
searchCircle=L.circle(CENTER,{radius:RADIUS,color:"#173d2b",weight:1,dashArray:"5 6",fill:false,interactive:false}).addTo(map);
const plannedLayer=L.geoJSON(null,{style:()=>({color:"#1680ff",weight:2,opacity:.9,fillColor:"#1680ff",fillOpacity:.08}),onEachFeature:(f,l)=>l.bindPopup(popup(f,"planned"))});
const performedLayer=L.geoJSON(null,{style:performedStyle,onEachFeature:(f,l)=>l.bindPopup(popup(f,"performed"))});
const samradPointLayer=L.geoJSON(null,{pointToLayer:(f,latlng)=>L.circleMarker(latlng,{radius:5,color:"#86198f",weight:1.5,fillColor:"#d946ef",fillOpacity:.85}),onEachFeature:(f,l)=>l.bindPopup(popup(f,"samrad"))});
const samradLineLayer=L.geoJSON(null,{style:()=>({color:"#ea580c",weight:3,opacity:.9}),onEachFeature:(f,l)=>l.bindPopup(popup(f,"samrad"))});
const samradAreaLayer=L.geoJSON(null,{style:()=>({color:"#a21caf",weight:2,opacity:.9,fillColor:"#d946ef",fillOpacity:.22}),onEachFeature:(f,l)=>l.bindPopup(popup(f,"samrad"))});
plannedLayer.addTo(map);performedLayer.addTo(map);
const esc=v=>String(v??"–").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const COLOR_LOW=[255,224,102],COLOR_HIGH=[153,0,76];
let performedScaleCache={mode:"none",min:null,max:null};
const CATEGORY_COLORS=["#e6007e","#ff6d00","#7b2cbf","#d00000","#6f1d1b","#f72585","#9d0208","#ffba08","#5a189a","#c1121f","#f77f00","#7209b7","#b5179e","#9a031e","#fb5607","#8338ec","#d90429","#ff9f1c"];
let categoryColorMap=new Map();
function performedYear(feature){
 const p=feature?.properties||{};
 const direct=Number(p.Arendear);
 if(Number.isFinite(direct)&&direct>=1900&&direct<=2100)return direct;
 const raw=p.Avvdatum;
 if(raw==null||raw==="")return null;
 const n=Number(raw);
 if(Number.isFinite(n)&&n>100000000000)return new Date(n).getUTCFullYear();
 const parsed=Date.parse(String(raw));
 return Number.isFinite(parsed)?new Date(parsed).getUTCFullYear():null;
}
function performedRatio(feature){
 const p=feature?.properties||{};
 const registered=Number(p.Arealha),reported=Number(p.AnmaldHa);
 if(p.Arealha==null||p.Arealha===""||p.AnmaldHa==null||p.AnmaldHa===""||!Number.isFinite(registered)||!Number.isFinite(reported)||registered<0||reported<=0)return null;
 return registered/reported*100;
}
function performedHectares(feature){
 const p=feature?.properties||{};
 const n=Number(p.Arealha);
 return p.Arealha!==null&&p.Arealha!==""&&Number.isFinite(n)&&n>=0?n:null;
}
function categoryValue(feature,mode){
 const p=feature?.properties||{};
 const raw=mode==="forestType"?p.Skogstyp:p.Avverktyp;
 const value=String(raw??"").trim();
 return value||"Okänd / saknas";
}
function categoryColor(value){
 if(!categoryColorMap.has(value)){
  const index=categoryColorMap.size;
  categoryColorMap.set(value,CATEGORY_COLORS[index%CATEGORY_COLORS.length]);
 }
 return categoryColorMap.get(value);
}
function mixColor(t){
 t=Math.max(0,Math.min(1,t));
 const rgb=COLOR_LOW.map((v,i)=>Math.round(v+(COLOR_HIGH[i]-v)*t));
 return "#"+rgb.map(v=>v.toString(16).padStart(2,"0")).join("");
}
function currentColorScale(){
 const mode=document.getElementById("performedColorMode")?.value||"none";
 const features=performedLayer.toGeoJSON().features||[];
 if(mode==="forestType"||mode==="harvestType"){
  const categories=[...new Set(features.map(f=>categoryValue(f,mode)))].sort((a,b)=>a.localeCompare(b,"sv"));
  categoryColorMap=new Map();
  categories.forEach(categoryColor);
  return {mode,categories};
 }
 const values=features.map(f=>mode==="year"?performedYear(f):mode==="ratio"?performedRatio(f):performedHectares(f)).filter(v=>v!==null);
 if(mode==="year")return {mode,min:values.length?Math.min(...values):null,max:2026};
 if(mode==="hectares"||mode==="ratio")return {mode,min:values.length?Math.min(...values):null,max:values.length?Math.max(...values):null};
 return {mode,min:null,max:null};
}
function performedStyle(feature){
 const mode=document.getElementById("performedColorMode")?.value||"none";
 if(mode==="none")return {color:"#e03131",weight:2,opacity:.95,fillColor:"#e03131",fillOpacity:.22};
 const scale=performedScaleCache;
 if(mode==="forestType"||mode==="harvestType"){
  const color=categoryColor(categoryValue(feature,mode));
  return {color:color,weight:2,opacity:.95,fillColor:color,fillOpacity:.62};
 }
 const value=mode==="year"?performedYear(feature):mode==="ratio"?performedRatio(feature):performedHectares(feature);
 if(value===null||scale.min===null||scale.max===null)return {color:"#7b8580",weight:2,opacity:.9,fillColor:"#aab3ae",fillOpacity:.4,dashArray:"3 3"};
 const t=scale.max===scale.min?1:(value-scale.min)/(scale.max-scale.min);
 const color=mixColor(t);
 return {color:color,weight:2,opacity:.95,fillColor:color,fillOpacity:.68};
}
function refreshPerformedColors(){
 const mode=document.getElementById("performedColorMode").value;
 const legend=document.getElementById("performedColorLegend");
 const minLabel=document.getElementById("legendMin"),maxLabel=document.getElementById("legendMax"),note=document.getElementById("legendNote");
 const scale=currentColorScale();
 performedScaleCache=scale;
 legend.style.display=mode==="none"?"none":"flex";
 const gradient=document.getElementById("legendGradient");
 const categoryLegend=document.getElementById("categoryLegend");
 categoryLegend.innerHTML="";
 if(mode==="year"){
  minLabel.style.display="";maxLabel.style.display="";gradient.style.display="";categoryLegend.style.display="none";
  minLabel.textContent=scale.min===null?"Äldst":String(scale.min);
  maxLabel.textContent="2026";
  note.textContent="år";
  gradient.style.background="linear-gradient(to right,"+mixColor(0)+","+mixColor(1)+")";
 }else if(mode==="hectares"||mode==="ratio"){
  minLabel.style.display="";maxLabel.style.display="";gradient.style.display="";categoryLegend.style.display="none";
  const unit=mode==="ratio"?" %":" ha";
  minLabel.textContent=scale.min===null?"Lägst":scale.min.toLocaleString("sv-SE",{maximumFractionDigits:2})+unit;
  maxLabel.textContent=scale.max===null?"Högst":scale.max.toLocaleString("sv-SE",{maximumFractionDigits:2})+unit;
  note.textContent=mode==="ratio"?"registrerad/anmäld":"inom valt område";
  gradient.style.background="linear-gradient(to right,"+mixColor(0)+","+mixColor(1)+")";
 }else if(mode==="forestType"||mode==="harvestType"){
  minLabel.style.display="none";maxLabel.style.display="none";gradient.style.display="none";categoryLegend.style.display="flex";
  note.textContent=mode==="forestType"?"Skogstyp":"Avverkningstyp";
  scale.categories.forEach(category=>{
   const item=document.createElement("span");
   item.style.display="inline-flex";item.style.alignItems="center";item.style.gap="5px";
   const swatch=document.createElement("i");
   swatch.style.display="inline-block";swatch.style.width="12px";swatch.style.height="12px";swatch.style.borderRadius="2px";swatch.style.background=categoryColor(category);
   const label=document.createElement("span");label.textContent=category;
   item.append(swatch,label);categoryLegend.append(item);
  });
 }
 performedLayer.setStyle(performedStyle);
}
function popup(f,type){
 const p=f.properties||{};
 const ratio=()=>{
  const registered=Number(p.Arealha),reported=Number(p.AnmaldHa);
  if(p.Arealha==null||p.Arealha===""||p.AnmaldHa==null||p.AnmaldHa===""||!Number.isFinite(registered)||!Number.isFinite(reported)||registered<=0)return "–";
  if(reported<=0)return "–";
  return (registered/reported*100).toLocaleString("sv-SE",{maximumFractionDigits:1})+" %";
 };
 if(type==="samrad"){
  const fields=[
   ["Ärendeår",p.ArendeAr??p.ArendeÅr],
   ["Beteckning",p.Beteckn],
   ["Kommun",p.Kommun],
   ["Status",p.Status],
   ["Inkomdatum",date(p.Inkomdatum)],
   ["Anmäld areal",ha(p.AnmaldHa)],
   ["Skogstyp",p.SkogsTyp??p.Skogstyp],
   ["Samrådsåtgärd",p.Samradsatgard]
  ];
  return '<div style="width:260px;max-width:260px;min-width:0;overflow-wrap:anywhere"><strong>Samråd</strong><table style="width:100%;table-layout:fixed;border-collapse:collapse;font-size:12px;margin-top:6px"><colgroup><col style="width:42%"><col style="width:58%"></colgroup>'+fields.map(([k,v])=>'<tr><td style="padding:3px 6px 3px 0;color:#59665e;vertical-align:top;overflow-wrap:anywhere;word-break:break-word">'+esc(k)+'</td><td style="padding:3px 0;vertical-align:top;overflow-wrap:anywhere;word-break:break-word"><b>'+esc(v)+'</b></td></tr>').join("")+'</table></div>';
 }
 const fields=type==="planned"?[
 ["Ärende",p.Beteckn],["Inkomdatum",date(p.Inkomdatum)],["Kommun",p.Kommun],["Avverkningstyp",p.Avverktyp],["Anmäld areal",ha(p.AnmaldHa)],["Status",p.ArendeStatus],["Skogstyp",p.Skogstyp],["Ändamål",p.Andamal],["Areal plantering",ha(p.SkogsodlHa)],["Areal naturlig föryngring",ha(p.NatforHa)],["Län",p.Lan]
 ]:[
 ["Ärendeår",p.Arendear],["Beteckning",p.Beteckn],["Kommun",p.Kommun],["Avverkningsdatum",date(p.Avvdatum)],["Registrerad areal",ha(p.Arealha)],["Anmäld areal",ha(p.AnmaldHa)],["Andel (registrerad/anmäld)",ratio()],["Avverkningstyp",p.Avverktyp],["Skogstyp",p.Skogstyp]
 ];
 return '<div style="width:260px;max-width:260px;min-width:0;overflow-wrap:anywhere;word-break:break-word"><strong>'+(type==="planned"?"Planerad avverkningsanmälan":"Utförd avverkning")+'</strong><table style="width:100%;table-layout:fixed;border-collapse:collapse;font-size:12px;margin-top:6px"><colgroup><col style="width:42%"><col style="width:58%"></colgroup>'+fields.map(([k,v])=>'<tr><td style="padding:3px 6px 3px 0;color:#59665e;vertical-align:top;overflow-wrap:anywhere;word-break:break-word">'+esc(k)+'</td><td style="padding:3px 0;vertical-align:top;overflow-wrap:anywhere;word-break:break-word"><b>'+esc(v)+'</b></td></tr>').join("")+'</table></div>';
}
function yearFromDateValue(value){
 if(value==null||value==="")return null;
 if(typeof value==="number"||/^\\d+(\\.\\d+)?$/.test(String(value).trim())){
  const n=Number(value);
  if(!Number.isFinite(n))return null;
  if(n>=100000000000)return new Date(n).getUTCFullYear();
  if(n>=1000000000)return new Date(n*1000).getUTCFullYear();
  if(n>=1900&&n<=2100)return Math.trunc(n);
 }
 const parsed=Date.parse(String(value));
 return Number.isFinite(parsed)?new Date(parsed).getUTCFullYear():null;
}
function updateDurationHistogram(features){
 const histogram=document.getElementById("durationHistogram");
 const summary=document.getElementById("durationSummary");
 const footnote=document.getElementById("durationFootnote");
 const records=[];
 let excluded=0;
 for(const feature of features){
  const p=feature?.properties||{};
  const issueYear=Number(p.Arendear);
  const harvestYear=yearFromDateValue(p.Avvdatum);
  if(!Number.isFinite(issueYear)||issueYear<1900||issueYear>2100||harvestYear===null||harvestYear<1900||harvestYear>2100){excluded++;continue;}
  const gap=issueYear-harvestYear;
  if(gap<0){excluded++;continue;}
  records.push(gap);
 }
 if(!records.length){
  summary.textContent="Inga utförda avverkningar med giltigt ärendeår och avverkningsdatum i det valda området.";
  histogram.innerHTML="";
  footnote.textContent=excluded?excluded.toLocaleString("sv-SE")+" polygoner kunde inte klassificeras.":"";
  return;
 }
 const buckets=[
  {label:"< 1 år",count:records.filter(n=>n===0).length},
  {label:"1–2 år",count:records.filter(n=>n===1).length},
  {label:"2–3 år",count:records.filter(n=>n===2).length},
  {label:"3–4 år",count:records.filter(n=>n===3).length},
  {label:"4–5 år",count:records.filter(n=>n===4).length},
  {label:"5+ år",count:records.filter(n=>n>=5).length}
 ];
 const max=Math.max(1,...buckets.map(b=>b.count));
 summary.textContent=records.length.toLocaleString("sv-SE")+" avverkningar med användbara årtal; andelar beräknas av dessa.";
 histogram.innerHTML=buckets.map(bucket=>{
  const pct=bucket.count/records.length*100;
  const width=bucket.count/max*100;
  return '<div class="duration-row"><div>'+bucket.label+'</div><div class="duration-track"><div class="duration-bar" style="width:'+width.toFixed(2)+'%"></div></div><div class="duration-value">'+pct.toLocaleString("sv-SE",{maximumFractionDigits:1})+' % ('+bucket.count.toLocaleString("sv-SE")+')</div></div>';
 }).join("");
 footnote.textContent="Andelarna summerar till 100 % över klassificerade polygoner. "+(excluded?excluded.toLocaleString("sv-SE")+" polygoner uteslutna eftersom årtal saknades, var ogiltiga eller avverkningsåret låg efter ärendeåret.":"");
}
function featureTouchesRadius(feature){
 const geometry=feature?.geometry;
 if(!geometry||!geometry.coordinates)return false;
 const center=L.latLng(CENTER[0],CENTER[1]);
 const insideRing=(point,ring)=>{
  let inside=false;
  const x=point[0],y=point[1];
  for(let i=0,j=ring.length-1;i<ring.length;j=i++){
   const xi=ring[i][0],yi=ring[i][1],xj=ring[j][0],yj=ring[j][1];
   const intersects=((yi>y)!==(yj>y))&&(x<(xj-xi)*(y-yi)/((yj-yi)||1e-15)+xi);
   if(intersects)inside=!inside;
  }
  return inside;
 };
 const pointInPolygon=(point,poly)=>{
  if(!poly.length||!insideRing(point,poly[0]))return false;
  for(let i=1;i<poly.length;i++)if(insideRing(point,poly[i]))return false;
  return true;
 };
 const pointToSegmentMeters=(p,a,b)=>{
  const lat0=center.lat*Math.PI/180;
  const xy=coord=>[ (coord[0]-CENTER[1])*111320*Math.cos(lat0), (coord[1]-CENTER[0])*110540 ];
  const P=xy(p),A=xy(a),B=xy(b);
  const dx=B[0]-A[0],dy=B[1]-A[1],den=dx*dx+dy*dy;
  const t=den?Math.max(0,Math.min(1,((P[0]-A[0])*dx+(P[1]-A[1])*dy)/den)):0;
  return Math.hypot(P[0]-(A[0]+t*dx),P[1]-(A[1]+t*dy));
 };
 const ringTouches=ring=>{
  if(!ring||ring.length<2)return false;
  for(let i=0;i<ring.length;i++){
   const a=ring[i],b=ring[(i+1)%ring.length];
   if(center.distanceTo(L.latLng(a[1],a[0]))<=RADIUS+2)return true;
   if(pointToSegmentMeters([CENTER[1],CENTER[0]],a,b)<=RADIUS+2)return true;
  }
  return false;
 };
 const ringTouchesOpen=ring=>{
  if(!ring||ring.length<1)return false;
  if(ring.length===1)return center.distanceTo(L.latLng(ring[0][1],ring[0][0]))<=RADIUS+2;
  for(let i=0;i<ring.length-1;i++){
   const a=ring[i],b=ring[i+1];
   if(center.distanceTo(L.latLng(a[1],a[0]))<=RADIUS+2||pointToSegmentMeters([CENTER[1],CENTER[0]],a,b)<=RADIUS+2)return true;
  }
  return false;
 };
 const polygonTouches=poly=>{
  if(!poly?.length)return false;
  const centerPoint=[CENTER[1],CENTER[0]];
  if(pointInPolygon(centerPoint,poly))return true;
  return poly.some(ring=>ringTouches(ring));
 };
 if(geometry.type==="Polygon")return polygonTouches(geometry.coordinates);
 if(geometry.type==="MultiPolygon")return geometry.coordinates.some(polygonTouches);
 if(geometry.type==="GeometryCollection")return (geometry.geometries||[]).some(g=>featureTouchesRadius({...feature,geometry:g}));
 if(geometry.type==="Point")return center.distanceTo(L.latLng(geometry.coordinates[1],geometry.coordinates[0]))<=RADIUS+2;
 if(geometry.type==="MultiPoint")return geometry.coordinates.some(c=>center.distanceTo(L.latLng(c[1],c[0]))<=RADIUS+2);
 if(geometry.type==="LineString")return ringTouchesOpen(geometry.coordinates);
 if(geometry.type==="MultiLineString")return geometry.coordinates.some(ringTouchesOpen);
 return false;
}
function filterToRadius(collection){
 const before=collection.features.length;
 collection.features=collection.features.filter(featureTouchesRadius);
 collection.filteredOutside=before-collection.features.length;
 return collection;
}
function date(v){if(v==null||v==="")return "–";let n=Number(v);if(Number.isFinite(n)&&n>100000000000)return new Date(n).toISOString().slice(0,10);return String(v)}
function ha(v){if(v==null||v==="")return "–";let n=Number(v);return Number.isFinite(n)?n.toLocaleString("sv-SE",{maximumFractionDigits:2})+" ha":String(v)}
function queryUrl(base,fields,bounds,offset){
 const params=new URLSearchParams({where:"1=1",outFields:fields,returnGeometry:"true",outSR:"4326",f:"geojson",resultRecordCount:"300",orderByFields:"OBJECTID"});
 params.set("geometry",JSON.stringify({xmin:bounds.getWest(),ymin:bounds.getSouth(),xmax:bounds.getEast(),ymax:bounds.getNorth(),spatialReference:{wkid:4326}}));
 params.set("geometryType","esriGeometryEnvelope");params.set("inSR","4326");params.set("spatialRel","esriSpatialRelIntersects");
 params.set("geometryPrecision","5");params.set("maxAllowableOffset","0.00003");
 params.set("resultOffset",String(offset));
 return base+"?"+params.toString();
}
async function getLayer(base,fields,bounds,signal){
 const all=[],seen=new Set();
 let offset=0,pages=0,hasMore=true,truncated=false;
 const pageSize=300,maxPages=20;
 while(hasMore&&pages<maxPages){
  const res=await fetch(queryUrl(base,fields,bounds,offset),{mode:"cors",signal});
  if(!res.ok)throw new Error("HTTP "+res.status);
  const json=await res.json();
  if(json.error)throw new Error(json.error.message||"Fel från karttjänsten");
  if(!Array.isArray(json.features))throw new Error("Karttjänsten returnerade inget GeoJSON-lager");
  let added=0;
  for(const feature of json.features){
   const id=feature.id??feature.properties?.OBJECTID;
   const key=id===undefined?JSON.stringify(feature.geometry):String(id);
   if(!seen.has(key)){seen.add(key);all.push(feature);added++;}
  }
  pages++;
  hasMore=Boolean(json.exceededTransferLimit)||json.features.length===pageSize;
  offset+=json.features.length;
  if(json.features.length===0||added===0){hasMore=false;truncated=json.features.length===pageSize;}
 }
 if(hasMore)truncated=true;
 return {type:"FeatureCollection",features:all,truncated,pages};
}
let viewRequestId=0,viewAbortController=null,viewDebounce=null;
async function load(){
 const requestId=++viewRequestId;
 if(viewAbortController)viewAbortController.abort();
 viewAbortController=new AbortController();
 const signal=viewAbortController.signal;
 const bounds=searchCircle.getBounds();
 document.getElementById("status").textContent="Hämtar polygoner inom "+(RADIUS/1000).toLocaleString("sv-SE")+" km från "+CENTER[0].toFixed(5)+", "+CENTER[1].toFixed(5)+"…";
 document.getElementById("reload").disabled=true;
 try{
  const wantSamrad=document.getElementById("showSamrad").checked;
  const [planned,performed,samradPoints,samradLines,samradAreas]=await Promise.all([
   getLayer(PLANNED,"OBJECTID,Lan,Kommunnr,Kommun,ArendeAr,Beteckn,Avverktyp,Andamal,Skogstyp,Inkomdatum,AnmaldHa,SkogsodlHa,NatforHa,ArendeStatus,AvvSasong,AvvHa",bounds,signal),
   getLayer(PERFORMED,"OBJECTID,Lannr,Lan,Kommunnr,Kommun,Arendear,Beteckn,Avverktyp,Skogstyp,AnmaldHa,SkogsodlHa,Natforha,Avvdatum,KallaDatum,KallaAreal,Forebild,Efterbild,Arealha",bounds,signal),
   wantSamrad?getLayer(SAMRAD_POINTS,"*",bounds,signal):Promise.resolve({type:"FeatureCollection",features:[],pages:0,truncated:false}),
   wantSamrad?getLayer(SAMRAD_LINES,"*",bounds,signal):Promise.resolve({type:"FeatureCollection",features:[],pages:0,truncated:false}),
   wantSamrad?getLayer(SAMRAD_AREAS,"*",bounds,signal):Promise.resolve({type:"FeatureCollection",features:[],pages:0,truncated:false})
  ]);
  if(requestId!==viewRequestId)return;
  filterToRadius(planned);filterToRadius(performed);
  if(wantSamrad){filterToRadius(samradPoints);filterToRadius(samradLines);filterToRadius(samradAreas);}
  plannedLayer.clearLayers();performedLayer.clearLayers();
  samradPointLayer.clearLayers();samradLineLayer.clearLayers();samradAreaLayer.clearLayers();
  plannedLayer.addData(planned);performedLayer.addData(performed);
  if(wantSamrad){samradPointLayer.addData(samradPoints);samradLineLayer.addData(samradLines);samradAreaLayer.addData(samradAreas);}
  refreshPerformedColors();
  updateDurationHistogram(performed.features);
  document.getElementById("plannedCount").textContent=planned.features.length.toLocaleString("sv-SE");
  document.getElementById("performedCount").textContent=performed.features.length.toLocaleString("sv-SE");
  document.getElementById("samradCount").textContent=wantSamrad?(samradPoints.features.length+samradLines.features.length+samradAreas.features.length).toLocaleString("sv-SE"):"av";

  const dates=performed.features.map(f=>Number(f.properties?.Avvdatum)).filter(n=>Number.isFinite(n)&&n>100000000000).sort((a,b)=>a-b);
  document.getElementById("dateRange").textContent=dates.length?new Date(dates[0]).toISOString().slice(0,10)+"–"+new Date(dates[dates.length-1]).toISOString().slice(0,10):"saknas";
  const samradPages=wantSamrad?samradPoints.pages+samradLines.pages+samradAreas.pages:0;
  const samradTruncated=wantSamrad&&(samradPoints.truncated||samradLines.truncated||samradAreas.truncated);
  document.getElementById("status").textContent="Visar objekt som skär eller tangerar sökcirkeln ("+planned.pages+" + "+performed.pages+(wantSamrad?" + "+samradPages:"")+" sidor). Filtrerade bort "+(planned.filteredOutside+performed.filteredOutside+(wantSamrad?samradPoints.filteredOutside+samradLines.filteredOutside+samradAreas.filteredOutside:0)).toLocaleString("sv-SE")+" objekt utanför radien."+
   ((planned.truncated||performed.truncated||samradTruncated)?" Varning: källans sidgräns kan ha nåtts; visat urval kan vara ofullständigt.":"");
 }catch(e){
  if(e?.name==="AbortError")return;
  if(requestId===viewRequestId)document.getElementById("status").textContent="Kunde inte hämta kartdata: "+e.message+". Kontrollera att Skogsstyrelsens tjänst är tillgänglig och tillåter anrop från webbläsaren.";
 }finally{
  if(requestId===viewRequestId){document.getElementById("reload").disabled=false;applyVisibility()}
 }
}
function scheduleViewLoad(){
 if(viewDebounce)clearTimeout(viewDebounce);
 viewDebounce=setTimeout(load,250);
}
function applyVisibility(){
 if(document.getElementById("showPlanned").checked){if(!map.hasLayer(plannedLayer))plannedLayer.addTo(map)}else map.removeLayer(plannedLayer);
 if(document.getElementById("showPerformed").checked){if(!map.hasLayer(performedLayer))performedLayer.addTo(map)}else map.removeLayer(performedLayer);
 const showSamrad=document.getElementById("showSamrad").checked;
 for(const layer of [samradAreaLayer,samradLineLayer,samradPointLayer]){
  if(showSamrad){if(!map.hasLayer(layer))layer.addTo(map)}else map.removeLayer(layer);
 }
}
document.getElementById("showPlanned").addEventListener("change",applyVisibility);document.getElementById("showPerformed").addEventListener("change",applyVisibility);
document.getElementById("showSamrad").addEventListener("change",()=>{applyVisibility();load()});document.getElementById("performedColorMode").addEventListener("change",refreshPerformedColors);document.getElementById("reload").addEventListener("click",load);document.getElementById("home").addEventListener("click",()=>{map.setView(CENTER,radiusZoom(RADIUS));});
function radiusZoom(radius){return radius<=2500?13:radius<=5000?12:radius<=10000?11:radius<=20000?10:radius<=50000?8:7;}
function applyArea(){
 const lat=Number(document.getElementById("lat").value),lon=Number(document.getElementById("lon").value),radius=Number(document.getElementById("radius").value);
 if(!Number.isFinite(lat)||lat < -90||lat>90||!Number.isFinite(lon)||lon < -180||lon>180||!Number.isFinite(radius)||radius<500||radius>100000){document.getElementById("status").textContent="Ange giltig latitud, longitud och radie.";return;}
 CENTER=[lat,lon];RADIUS=radius;searchCircle.setLatLng(CENTER).setRadius(RADIUS);map.fitBounds(searchCircle.getBounds(),{padding:[20,20]});load();
}
document.getElementById("applyArea").addEventListener("click",applyArea);
document.getElementById("radius").addEventListener("change",applyArea);
map.on("click",e=>{document.getElementById("lat").value=e.latlng.lat.toFixed(5);document.getElementById("lon").value=e.latlng.lng.toFixed(5);applyArea();});
// Area selection, not incidental pan/zoom, controls the query extent.
// This makes the returned features match the explicitly selected center and radius.
map.on("baselayerchange",applyVisibility);
load();
})();

"""Consolida resultados publicados; no entrena ni modifica métricas originales."""
import argparse
import base64
import csv
import hashlib
import itertools
import json
from pathlib import Path
import platform
import shutil
import warnings

import numpy as np
import scipy
from scipy.stats import wilcoxon
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LABELS={'E0':'NaN nativo','E1':'Media','E2':'Mediana','E3':'Moda','E4':'Forward fill',
        'E5':'Ridge 60k/10/25','E6':'miceforest','ZERO':'Ceros',
        'FF_IND':'FF + indicadores','FF_MED_POST':'FF + mediana posterior',
        'FF_LIMIT2ROWS':'FF límite 2 filas','FF_ZERO':'FF + cero','FF_MED_PRE':'FF + mediana previa'}
ORDER=list(LABELS)
FAMILIES={'EXP1':{'label':'Exp1 · marzo–agosto','train':[201903,201904,201905,201906,201907,201908],
                 'trees':280,'n':4323,'indicators':'Sin indicadores adicionales, salvo FF_IND'},
          'EXP2':{'label':'Exp2 · indicadores y derivados','train':[201903,201904,201905,201906,201907,201908],
                  'trees':361,'n':4352,'indicators':'150 indicadores + 300 lags + 300 deltas'},
          'HIST_MJ':{'label':'Histórico · marzo–junio','train':[201903,201904,201905,201906],
                     'trees':280,'n':4323,'indicators':'Sin indicadores adicionales, salvo FF_IND; árboles declarados por scripts'}}
SEED_FIELDS=['roc_auc','pr_auc','auc_baja2','ap_baja2','n_fijo_evaluado','gain_at_n_fijo',
             'lift_at_n_fijo','recall_baja2_at_n_fijo','precision_baja2_at_n_fijo','baja2_capturadas_at_n_fijo']
BASE_MAP={**{f'E{i}':f'E{i}' for i in range(6)},'E06':'E6','E7':'ZERO'}
MICA_MAP={'E0':'E0','E4':'E4','E9':'FF_IND','E10':'FF_MED_POST','E12':'FF_LIMIT2ROWS'}
FLOR_MAP={'E0':'E0','E4':'E4','FF_ZERO':'FF_ZERO','FF_MEDIAN_MICA':'FF_MED_POST','FF_MEDIAN':'FF_MED_PRE'}
COLORS={'E0':'#161a20','E1':'#8b99aa','E2':'#7089a7','E3':'#9c8b78','E4':'#576c88',
        'E5':'#df3211','E6':'#a77988','ZERO':'#b3a048','FF_IND':'#659698','FF_MED_POST':'#dc6b48',
        'FF_LIMIT2ROWS':'#819c65','FF_ZERO':'#df9c24','FF_MED_PRE':'#ad809c'}


def readcsv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def writecsv(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:return
    cols=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader();writer.writerows(rows)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def holm(rows):
    last=0.
    for rank,row in enumerate(sorted(rows,key=lambda r:r['p_raw'])):
        last=min(1.,max(last,row['p_raw']*(len(rows)-rank)))
        row['p_holm']=last;row['family_size']=len(rows);row['significant_005']=last<.05
    return rows


def paired(a,b,metric):
    d=np.array(a,dtype=float)-np.array(b,dtype=float)
    # Evitar empates espurios por la representación de CSV flotantes.
    d=np.round(d,12 if metric=='roc_auc' else 6)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        p=1. if np.all(d==0) else float(wilcoxon(d,zero_method='zsplit',alternative='two-sided',method='auto').pvalue)
    if not np.isfinite(p):raise ValueError('p no finito')
    return {'delta_mean':float(d.mean()),'delta_median':float(np.median(d)),
            'wins':int((d>0).sum()),'ties':int((d==0).sum()),'losses':int((d<0).sum()),'p_raw':p}


def build(inputs,out):
    inputs,out=Path(inputs),Path(out)
    data_dir=out/'consolidado/datos';data_dir.mkdir(parents=True,exist_ok=True)
    raw_dir=out/'consolidado/fuentes';raw_dir.mkdir(parents=True,exist_ok=True)
    source_spec=inputs/'entradas.json'
    if source_spec.exists():
        sources=[(x['family'],x['source'],inputs/x['seed_csv'],inputs/x['ensemble_csv'],x['mapping'],x['flor']) for x in json.loads(source_spec.read_text(encoding='utf-8'))]
    else:
        sources=[]
        for label,folder in [('EXP1','exp_01_imputacion'),('EXP2','exp_02_indicadores_missing')]:
            sources.append((label,'agustin_'+label,inputs/'agustin'/folder/'resultados/metricas_por_semilla_test.csv',
                            inputs/'agustin'/folder/'resultados/resumen_ensamble_test.csv',BASE_MAP,False))
        for family,dirname in [('EXP1','exp_missings_marzo_agosto'),('HIST_MJ','exp_missings_marzo_junio')]:
            root=inputs/'mica/extraidos'/dirname
            sources.append((family,'mica_'+dirname,next(root.glob('*metricas_por_semilla*csv')),next(root.glob('*resumen_ensamble*csv')),MICA_MAP,False))
        sources.extend([
            ('EXP1','flor_alineado',inputs/'flor/outputs/metricas_por_semilla.csv',inputs/'flor/outputs/resumen_florencia.csv',FLOR_MAP,True),
            ('EXP1','flor_original',inputs/'flor/archivo_corrida_original/outputs/metricas_por_semilla.csv',
             inputs/'flor/archivo_corrida_original/outputs/resumen_florencia.csv',FLOR_MAP,True)])
    spec=[{'family':f,'source':s,'seed_csv':s+'/'+a.name,'ensemble_csv':s+'/'+b.name,'mapping':m,'flor':fl} for f,s,a,b,m,fl in sources]
    (raw_dir/'entradas.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
    seed_rows={};ensembles={};provenance={};checks=[];source_manifest=[]
    expected_seeds=None
    for family,source,seedfile,ensfile,mapping,flor in sources:
        srows=readcsv(seedfile);erows=readcsv(ensfile)
        for path in [seedfile,ensfile]:
            dest=raw_dir/source/path.name;dest.parent.mkdir(parents=True,exist_ok=True)
            if path.resolve()!=dest.resolve():shutil.copyfile(path,dest)
            source_manifest.append({'source':source,'file':dest.relative_to(out).as_posix(),'sha256':sha(dest)})
        grouped={}
        for row in srows:
            if row['method'] not in mapping:raise ValueError('Método sin correspondencia: '+row['method'])
            canonical=mapping[row['method']]
            normalized={'family':family,'method':canonical,'method_uid':family+'::'+canonical,
                        'label':LABELS[canonical],'seed':int(row['seed'])}
            for key in SEED_FIELDS:normalized[key]=float(row[key])
            if normalized['n_fijo_evaluado']!=FAMILIES[family]['n']:raise ValueError('N incompatible')
            grouped.setdefault(canonical,[]).append(normalized)
            provenance.setdefault((family,canonical),set()).add(source+':'+row['method'])
        for canonical,rows in grouped.items():
            rows.sort(key=lambda r:r['seed'])
            seeds=[r['seed'] for r in rows]
            if len(seeds)!=30 or len(set(seeds))!=30:raise ValueError('No hay 30 semillas únicas')
            if expected_seeds is None:expected_seeds=seeds
            if seeds!=expected_seeds:raise ValueError('Semillas distintas')
            key=(family,canonical)
            if key in seed_rows:
                max_auc=max(abs(a['roc_auc']-b['roc_auc']) for a,b in zip(seed_rows[key],rows))
                max_gain=max(abs(a['gain_at_n_fijo']-b['gain_at_n_fijo']) for a,b in zip(seed_rows[key],rows))
                for metric in SEED_FIELDS:
                    tol=1e-6 if metric=='gain_at_n_fijo' else 1e-10
                    if not np.allclose([a[metric] for a in seed_rows[key]],[a[metric] for a in rows],rtol=0,atol=tol):
                        raise ValueError(f'Control incompatible {key} {source} {metric}')
                checks.append({'family':family,'method':canonical,'source':source,'n_seeds':30,
                               'max_auc_diff':max_auc,'max_gain_diff':max_gain,'verified':True})
            else:seed_rows[key]=rows
        for row in erows:
            m=mapping[row['method']];key=(family,m)
            auc=float(row['auc_ensemble'] if flor else row['roc_auc'])
            gain=float(row['gain_ensemble'] if flor else row['gain_at_n_fijo'])
            cap=(gain-FAMILIES[family]['n']*(-27500))/1100000
            if abs(cap-round(cap))>1e-8:raise ValueError('Ganancia no corresponde a contactos enteros')
            e={'auc_ensemble':auc,'gain_ensemble':gain,'baja2_ensemble':int(round(cap))}
            if key in ensembles:
                if not np.isclose(ensembles[key]['auc_ensemble'],auc,rtol=0,atol=1e-10) or ensembles[key]['gain_ensemble']!=gain:
                    raise ValueError('Ensamble repetido incompatible: '+str(key))
            else:ensembles[key]=e
    ordered=sorted(seed_rows,key=lambda k:(list(FAMILIES).index(k[0]),ORDER.index(k[1])))
    summary=[];catalog=[]
    for key in ordered:
        family,m=key;rows=seed_rows[key]
        r={'family':family,'method':m,'method_uid':family+'::'+m,'label':LABELS[m],
           'train_months':','.join(map(str,FAMILIES[family]['train'])),'test_month':201910,
           'trees':FAMILIES[family]['trees'],'n':FAMILIES[family]['n'],'seeds':30,
           'auc_mean':float(np.mean([x['roc_auc'] for x in rows])),
           'auc_sd':float(np.std([x['roc_auc'] for x in rows],ddof=1)),
           'gain_mean':float(np.mean([x['gain_at_n_fijo'] for x in rows])),
           'gain_sd':float(np.std([x['gain_at_n_fijo'] for x in rows],ddof=1)),**ensembles[key]}
        summary.append(r)
        catalog.append({k:r[k] for k in ['family','method','method_uid','label','train_months','test_month','trees','n','seeds']}
                       |{'source_aliases':' | '.join(sorted(provenance[key])),'status':'published',
                         'individual_predictions_available':False if m.startswith('FF_') else family in ['EXP1','EXP2']})
    tests=[]
    for family in FAMILIES:
        methods=[m for f,m in ordered if f==family]
        ff=[m for m in methods if m.startswith('FF_')]
        specs=[('vs_E0',[(m,'E0') for m in methods if m!='E0']),
               ('ff_vs_E4',[(m,'E4') for m in ff]),
               ('all_pairs',list(itertools.combinations(methods,2)))]
        for name,pairs in specs:
            for metric in ['gain_at_n_fijo','roc_auc']:
                rows=[]
                for a,b in pairs:
                    rows.append({'family':family,'test_family':name,'metric':metric,'method':a,'reference':b,'n_pairs':30,
                                 **paired([r[metric] for r in seed_rows[(family,a)]],
                                          [r[metric] for r in seed_rows[(family,b)]],metric)})
                tests.extend(holm(rows))
    writecsv(data_dir/'metricas_por_semilla.csv',[r for k in ordered for r in seed_rows[k]])
    writecsv(data_dir/'resumen_unificado.csv',summary)
    writecsv(data_dir/'catalogo_metodos.csv',catalog)
    writecsv(data_dir/'tests_pareados_holm.csv',tests)
    writecsv(data_dir/'controles_reproducidos.csv',checks)
    for name in ['vs_E0','ff_vs_E4','all_pairs']:
        writecsv(data_dir/f'tests_{name}.csv',[r for r in tests if r['test_family']==name])
    report={'sources':source_manifest,'families':FAMILIES,'seed_values':expected_seeds,
        'unique_methods':len(summary),'seed_rows':sum(len(x) for x in seed_rows.values()),'tests':len(tests),
        'duplicate_controls_validated':checks,'deduplicated_seed_rows':30*len(checks),
        'statistics':{'test':'paired two-sided Wilcoxon','zero_method':'zsplit','method':'auto',
                      'auc_difference_rounding_decimals':12,'gain_difference_rounding_decimals':6,
                      'adjustment':'Holm separately by family, contrast set and metric',
                      'inferential_unit':'LightGBM seed conditional on the same October clients; not temporal replication'},
        'environment':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__},
        'limitations':['No cross-family significance tests: train/hyperparameters/N differ.',
                       'No ensemble/client-level tests for FF until predictions are supplied.',
                       'Mica FF limit=2 is a limit of consecutive null rows, not guaranteed calendar months.',
                       'Median before FF and median after FF are separate methods.',
                       'Historical March-June configuration has published CSV and scripts, but no complete run identity in ZIP.',
                       'Ridge parameter variants and business rules remain pending verified result files.']}
    (data_dir/'validacion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    make_figures(out,summary,seed_rows,tests)
    make_dashboard(out,summary,seed_rows,tests,report)
    return report,summary,tests


def make_figures(out,summary,seed_rows,tests):
    dest=out/'consolidado/figuras';dest.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
        'axes.spines.right':False,'axes.spines.left':False,'axes.labelcolor':'#30343c','text.color':'#20242a',
        'axes.edgecolor':'#c5cad2','savefig.facecolor':'white'})
    lookup={(r['family'],r['method']):r for r in summary}
    def save(fig,name):
        fig.savefig(dest/(name+'.png'),dpi=180,bbox_inches='tight')
        fig.savefig(dest/(name+'.svg'),bbox_inches='tight');plt.close(fig)
    # Ganancia media base: mismo gráfico, p de la familia completa de su experimento.
    methods=['E1','E2','E3','E4','E5','E6','ZERO']
    fig,ax=plt.subplots(figsize=(11.5,3.5));x=np.arange(len(methods));width=.34
    for k,(family,color) in enumerate([('EXP1','#6e7885'),('EXP2','#df3211')]):
        base=lookup[(family,'E0')]['gain_mean']
        vals=[(lookup[(family,m)]['gain_mean']-base)/1e6 for m in methods]
        bars=ax.bar(x+(k-.5)*width,vals,width,label=family,color=color)
        for j,(m,v) in enumerate(zip(methods,vals)):
            t=next(t for t in tests if t['family']==family and t['test_family']=='vs_E0' and t['metric']=='gain_at_n_fijo' and t['method']==m)
            if t['p_holm']<.05:ax.text(bars[j].get_x()+width/2,v+(.15 if v>=0 else -.3),'*',ha='center',fontweight='bold')
    ax.axhline(0,color='#555',lw=.8);ax.set_xticks(x,[m if m!='ZERO' else 'Ceros' for m in methods]);ax.set_ylabel('Δ ganancia media vs E0 (M$)')
    ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True);ax.legend(frameon=False,ncol=2,loc='upper left');fig.tight_layout();save(fig,'base_delta_media')
    # Una escala y misma simbología para las dos familias, sin tests entre familias.
    for family in FAMILIES:
        rows=[r for r in summary if r['family']==family]
        fig,ax=plt.subplots(figsize=(11.5,4.9 if family=='EXP1' else 3.5))
        y=np.arange(len(rows));ax.scatter([r['gain_mean']/1e6 for r in rows],y,label='Media de 30 semillas',marker='o',s=36,color='#6e7885')
        ax.scatter([r['gain_ensemble']/1e6 for r in rows],y,label='Ensamble',marker='D',s=36,color='#df3211')
        for i,r in enumerate(rows):ax.plot([r['gain_mean']/1e6,r['gain_ensemble']/1e6],[i,i],color='#ccd1d8',zorder=0)
        ax.set_yticks(y,[LABELS[r['method']] for r in rows]);ax.invert_yaxis();ax.set_xlabel('Ganancia al N congelado (M$)')
        ax.grid(axis='x',alpha=.15);ax.legend(frameon=False,ncol=2,loc='lower right');fig.tight_layout();save(fig,'ganancias_'+family.lower())
    ff=['FF_IND','FF_MED_POST','FF_LIMIT2ROWS','FF_ZERO','FF_MED_PRE']
    fig,ax=plt.subplots(figsize=(8.5,3.5));base=lookup[('EXP1','E4')]['gain_mean']
    vals=[(lookup[('EXP1',m)]['gain_mean']-base)/1e6 for m in ff]
    ax.barh(range(len(ff)),vals,color=[COLORS[m] for m in ff]);ax.set_yticks(range(len(ff)),[LABELS[m] for m in ff]);ax.invert_yaxis()
    ax.axvline(0,color='#666',lw=.8);ax.set_xlabel('Δ ganancia media vs forward fill (M$)');ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    for i,v in enumerate(vals):ax.text(v+(.03 if v>=0 else -.03),i,f'{v:+.2f}',ha='left' if v>=0 else 'right',va='center',fontsize=9)
    fig.tight_layout();save(fig,'ff_delta_media')
    # Dispersión de modelos individuales, sin presentarla como incertidumbre temporal.
    rows=[r for r in summary if r['family']=='EXP1'];fig,ax=plt.subplots(figsize=(11.5,5))
    rng=np.random.default_rng(20261118)
    for i,r in enumerate(rows):
        v=[x['gain_at_n_fijo']/1e6 for x in seed_rows[('EXP1',r['method'])]]
        ax.scatter(v,i+rng.uniform(-.16,.16,len(v)),s=10,alpha=.5,color=COLORS[r['method']]);ax.scatter(np.mean(v),i,s=40,color='black',marker='|')
    ax.set_yticks(range(len(rows)),[r['label'] for r in rows]);ax.invert_yaxis();ax.set_xlabel('Ganancia por semilla (M$)');ax.grid(axis='x',alpha=.15);fig.tight_layout();save(fig,'dispersion_semillas_exp1')


def make_dashboard(out,summary,seed_rows,tests,report):
    docs=out/'docs';docs.mkdir(parents=True,exist_ok=True)
    vendor=out.parent/'vendor/plotly.min.js'
    if not vendor.exists():vendor=out/'e7_ceros_gcp/vendor/plotly.min.js'
    if not vendor.exists():vendor=Path(__file__).resolve().parents[1]/'E7_ceros_GCP/vendor/plotly.min.js'
    payload={'summary':summary,'seeds':[r for rows in seed_rows.values() for r in rows],
             'tests':[r for r in tests if r['test_family']!='all_pairs'],'labels':LABELS,'families':FAMILIES}
    data=json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
    csvs={p.name:base64.b64encode(p.read_bytes()).decode() for p in (out/'consolidado/datos').glob('*.csv')}
    page='''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Resultados colaborativos unificados</title><style>body{font:15px system-ui;background:#f3f5f8;color:#202a3b;margin:0}main{max-width:1450px;padding:28px;margin:auto}h1{font-size:30px}h2{font-size:21px}section{background:white;border:1px solid #dce2eb;border-radius:10px;padding:22px;margin:20px 0}p{line-height:1.6}select{font:inherit;padding:9px;border:1px solid #b7c5d8;border-radius:6px}.scroll{overflow:auto;max-height:560px}table{border-collapse:collapse;white-space:nowrap;width:100%;font-size:13px}th,td{padding:9px 12px;border-bottom:1px solid #e3e7ed;text-align:right}th{position:sticky;top:0;background:#edf1f7}th:first-child,td:first-child{text-align:left}.plot{height:560px}a{color:#285b9a}.links a{display:inline-block;margin:6px 15px 6px 0}.note{border-left:3px solid #df3211;padding-left:14px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}@media(max-width:900px){.grid{grid-template-columns:1fr}main{padding:14px}}</style><script src="data:text/javascript;base64,@@VENDOR@@"></script></head><body><main><h1>Experimentos colaborativos · resultados unificados</h1><p>Agustín, Micaela y Florencia · octubre 2019 · 30 semillas por método. Los controles repetidos se verifican y se cuentan una sola vez.</p><p><a href="index.html">Portada</a> · <a href="https://github.com/AgustinBerna/experimentos-colaborativos/tree/main/consolidado">Código, fuentes y metodología</a> · <a href="https://docs.google.com/presentation/d/1VafvO0apPP7rRcx2Trlw8Ni1e_sXKFbhVI6a6_HfJ68">Slides</a></p><section><label>Familia <select id="family"><option value="EXP1">Exp1 + extensiones FF · marzo–agosto</option><option value="EXP2">Exp2 · indicadores y derivados</option><option value="HIST_MJ">Histórico · marzo–junio</option></select></label><p id="conditions"></p><p class="note">Las familias conservan sus propias condiciones. No se calculan tests entre Exp1 y Exp2 ni entre ventanas de entrenamiento. Cambian los hiperparámetros, árboles o meses; Exp2 también usa otro N.</p></section><section><h2>Media de semillas y ensamble</h2><p>Son evaluaciones distintas: el ensamble promedia probabilidades y forma una única campaña. Su ganancia no es la media de las ganancias.</p><div id="means" class="plot"></div><div class="scroll"><table id="summary"></table></div></section><section><h2>Variación entre semillas</h2><p>Los puntos comparten clientes y mes; no representan meses independientes.</p><div id="seeds" class="plot"></div></section><section><h2>Tests pareados unificados</h2><label>Familia de contrastes <select id="contrast"><option value="vs_E0">Cada alternativa vs NaN nativo</option><option value="ff_vs_E4">Variantes FF vs forward fill</option></select></label><p>Wilcoxon bilateral, diferencias redondeadas para evitar empates espurios, zero_method=zsplit y Holm separado por familia, conjunto de contrastes y métrica. No son tests sobre las ganancias de los ensambles.</p><div class="scroll"><table id="tests"></table></div></section><section><h2>Definiciones y trazabilidad</h2><p>“Ceros” se diferencia de “FF + cero”. FF + mediana previa usa observaciones originales de train; FF + mediana posterior calcula la mediana después de arrastrar valores. Se conservan ambas definiciones, sin fusionarlas.</p><p>El límite de FF de Mica se implementa con forward_fill(limit=2): dos registros consecutivos faltantes; no garantiza dos meses calendario cuando hay huecos.</p><p>Los IDs antiguos E7/E8/E9/E10/E12 se mapean a identificadores únicos en catalogo_metodos.csv. Los p-valores pueden diferir de los repositorios originales porque ahora se ajusta una familia conjunta más grande.</p><p class="note">Pendiente: predicciones por cliente de las extensiones FF para la comparación unificada de ensambles. Variantes Ridge y reglas de negocio: sin resultados nuevos verificados; no se incluyen como métodos terminados.</p><div class="links" id="downloads"></div></section></main><script id="data" type="application/json">@@DATA@@</script><script>(()=>{'use strict';const D=JSON.parse(document.getElementById('data').textContent);const C=@@CSVS@@;const f=(x,n=3)=>x===null||x===undefined?'—':Number(x).toLocaleString('es-AR',{maximumFractionDigits:n,minimumFractionDigits:n});function table(id,headers,rows){const el=document.getElementById(id);el.replaceChildren();const h=document.createElement('thead'),tr=document.createElement('tr');headers.forEach(x=>{const th=document.createElement('th');th.textContent=x;tr.appendChild(th)});h.appendChild(tr);el.appendChild(h);const b=document.createElement('tbody');rows.forEach(row=>{const tr=document.createElement('tr');row.forEach(x=>{const td=document.createElement('td');td.textContent=x;tr.appendChild(td)});b.appendChild(tr)});el.appendChild(b)}function update(){const fam=document.getElementById('family').value,kind=document.getElementById('contrast').value;const rows=D.summary.filter(r=>r.family===fam),info=D.families[fam];document.getElementById('conditions').textContent=info.label+' · '+info.trees+' árboles · N='+info.n+' · '+rows.length+' métodos únicos';table('summary',['Método','AUC media','AUC ensamble','Ganancia media ($M)','Desvío ($M)','Ensamble ($M)','BAJA+2 ensamble'],rows.map(r=>[r.label,f(r.auc_mean,6),f(r.auc_ensemble,6),f(r.gain_mean/1e6),f(r.gain_sd/1e6),f(r.gain_ensemble/1e6),r.baja2_ensemble]));const layout={margin:{l:215,t:20,b:60,r:30},font:{family:'system-ui'},xaxis:{title:'Ganancia (M$)'},yaxis:{autorange:'reversed'},legend:{orientation:'h',y:-.15}};Plotly.react('means',[{type:'scatter',mode:'markers',name:'Media de semillas',x:rows.map(r=>r.gain_mean/1e6),y:rows.map(r=>r.label),marker:{color:'#697887',size:9}},{type:'scatter',mode:'markers',name:'Ensamble',x:rows.map(r=>r.gain_ensemble/1e6),y:rows.map(r=>r.label),marker:{color:'#df3211',symbol:'diamond',size:9}}],layout,{responsive:true,displaylogo:false});Plotly.react('seeds',rows.map(r=>({type:'box',orientation:'h',name:r.label,x:D.seeds.filter(s=>s.family===fam&&s.method===r.method).map(s=>s.gain_at_n_fijo/1e6),boxpoints:'all',marker:{size:3},jitter:.3})),{...layout,showlegend:false},{responsive:true,displaylogo:false});const tests=D.tests.filter(r=>r.family===fam&&r.test_family===kind);table('tests',['Método','Referencia','Métrica','Δ media','Gana / empata / pierde','p bruto','p Holm','Contrastes'],tests.map(r=>[D.labels[r.method],D.labels[r.reference],r.metric==='roc_auc'?'AUC':'Ganancia ($M)',f(r.delta_mean/(r.metric==='roc_auc'?1:1e6),r.metric==='roc_auc'?6:3),r.wins+' / '+r.ties+' / '+r.losses,f(r.p_raw,6),f(r.p_holm,6),r.family_size]));document.body.dataset.rendered='ok'}document.getElementById('family').addEventListener('change',update);document.getElementById('contrast').addEventListener('change',update);for(const [name,b64]of Object.entries(C)){const a=document.createElement('a');a.textContent=name;a.download=name;a.href='data:text/csv;base64,'+b64;document.getElementById('downloads').appendChild(a)}update();})();</script></body></html>'''
    page=page.replace('@@VENDOR@@',base64.b64encode(vendor.read_bytes()).decode()).replace('@@DATA@@',data).replace('@@CSVS@@',json.dumps(csvs))
    (docs/'consolidado.html').write_text(page,encoding='utf-8')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--fuentes',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();report,summary,tests=build(args.fuentes,args.out)
    print(json.dumps({'methods':report['unique_methods'],'seed_rows':report['seed_rows'],'tests':report['tests'],'duplicates':len(report['duplicate_controls_validated'])}))


if __name__=='__main__':main()

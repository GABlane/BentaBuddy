#!/usr/bin/env python3
import os,tempfile,json,subprocess,sys,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description='Real model smoke tests for all business themes in an isolated database.')
parser.add_argument('--cli',type=Path,help='Use llama-completion instead of HTTP; does not test the running server/browser.')
parser.add_argument('--theme',choices=['bakery','gadgets','staycation','general'])
args=parser.parse_args()
sys.path.insert(0,str(ROOT))
workspace=tempfile.TemporaryDirectory()
os.environ['BENTABUDDY_DATA']=workspace.name
from backend import app as backend
from backend.business import ensure_catalog
cases=[
 ('bakery','Pa-order 2 dozen cheese pandesal November 20, 2026, pickup 9am. Two separate gift boxes po.','p_pandesal'),
 ('gadgets','Pa-order 2 USB-C cables November 20, 2026, pickup 10am. Black color po.','p_gadgets_starter_cable'),
 ('staycation','Pa-book studio unit for 2 guests, check-in November 20, 2026 at 2pm, check-out November 22, 2026.','p_staycation_starter_studio'),
 ('general','Order po 1 Your service on November 20, 2026 at 10am. Pickup po, service location: customer office.','p_general_starter_service'),
]
for kind,message,expected in cases:
 if args.theme and kind!=args.theme:continue
 with backend.connect() as db:
  ensure_catalog(db,kind)
  db.execute("INSERT OR REPLACE INTO settings VALUES ('business_profile',?)",(json.dumps({'kind':kind,'name':'Smoke test'}),))
  products=backend.payloads(db,'products')
 conv={'id':'smoke','messages':[{'id':'smoke_message','text':message,'created_at':'2026-10-10T06:00:00+08:00'}],'is_demo':False}
 endpoint,body=backend.extraction_request(conv,products,None)
 request=os.path.join(workspace.name,'request.json')
 with open(request,'w') as stream:json.dump(body,stream)
 if args.cli:
  prompt=''.join('<|im_start|>'+m['role']+'\n'+m['content']+'<|im_end|>\n' for m in body['messages'])+'<|im_start|>assistant\n'
  prompt_path=Path(workspace.name)/'prompt.txt';prompt_path.write_text(prompt)
  schema_path=Path(workspace.name)/'schema.json';schema_path.write_text(json.dumps(body.get('response_format',{}).get('json_schema',{}).get('schema',body.get('format',backend.SCHEMA))))
  response=subprocess.run([str(args.cli.resolve()),'-m',str(ROOT/'.runtime/models/qwen3-4b-instruct-2507.gguf'),'-f',str(prompt_path),'-jf',str(schema_path),'-n','1000','-c','4096','-t','4','--device','none','-ngl','0','--no-op-offload','--no-kv-offload','--fit','off','--temp','0','--no-display-prompt','--no-conversation'],capture_output=True,text=True,timeout=240,stdin=subprocess.DEVNULL)
  if response.returncode:raise RuntimeError(response.stderr[-700:])
  content=response.stdout.strip().removesuffix('[end of text]').strip()
  raw={'choices':[{'finish_reason':'stop','message':{'content':content}}]}
 else:
  response=subprocess.run(['curl','--fail','--silent','--show-error','--max-time','120','http://127.0.0.1:11434'+endpoint,'-H','Content-Type: application/json','--data-binary','@'+request],capture_output=True,text=True)
  if response.returncode:raise RuntimeError('Model transport unavailable: '+response.stderr[:180])
  raw=json.loads(response.stdout)
 try:
  proposal=backend.parse_model_response(raw,backend.RUNTIME)
  with backend.connect() as db:proposal=backend.validate_proposal(db,proposal,conv)
  assert expected in [i['product_id'] for i in proposal['items']],proposal
  assert len(proposal['items'])==1,proposal
  expected_quantity=1 if kind=='general' else 2
  assert proposal['items'][0]['quantity']==expected_quantity,proposal
  if kind=='general':assert 'customer office' in proposal['notes'].lower(),proposal
  if kind=='gadgets':assert 'black' in proposal['notes'].lower(),proposal
  if kind=='bakery':assert 'gift boxes' in proposal['notes'].lower(),proposal
  if kind=='staycation':
   assert proposal.get('reservation'),proposal
   assert proposal['reservation']['check_in']=='2026-11-20',proposal
   assert proposal['reservation']['check_out']=='2026-11-22',proposal
   assert proposal['reservation']['guests']==2,proposal
  print(kind+': PASS '+json.dumps({'action':proposal['action'],'items':proposal['items'],'reservation':proposal.get('reservation'),'notes':proposal['notes']}),flush=True)
 except Exception as error:
  print(kind+': FAIL '+str(error)[:900],flush=True)
  if args.cli:print('Synthetic model output: '+content[:1600],flush=True)
  raise

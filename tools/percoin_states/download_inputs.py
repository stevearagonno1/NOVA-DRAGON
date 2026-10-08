import pathlib,urllib.request,hashlib,json
P=pathlib.Path(__file__).parent
sources={'BTC':('data/BTCUSDT_1m.parquet','3d7c5d3f6c8f2dd45b2f53922a92d4d5f3930f23',5033588),'ETH':('crypto_archive/ETHUSDT_1m.parquet','4f458623833ad59f94a3cdd65d9f3511d660ce7b',75174110)}
for asset,(path,blob,size) in sources.items():
 p=P/(asset+'.parquet')
 if not p.exists():
  u='https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/6d0226a03b84656e14b94dd8a37e39332cc2f68f/'+path
  b=urllib.request.urlopen(u,timeout=40).read();assert len(b)==size and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==blob;p.write_bytes(b)
 print(json.dumps({'asset':asset,'bytes':p.stat().st_size,'blob':blob}),flush=True)

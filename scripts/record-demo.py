"""Capture real CLI output through an isolated PTY, then render a readable replay.
No desktop automation. No synthetic command results. Presentation holds are added.
Requires Pillow, ffmpeg; intended for the maintainer's macOS release workstation.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import datetime,fcntl,hashlib,json,os,pty,re,select,shutil,struct,subprocess,tarfile,termios,time,unicodedata
ROOT=Path(__file__).resolve().parents[1];version=(ROOT/"VERSION").read_text().strip()
work=ROOT/"build/media";work.mkdir(parents=True,exist_ok=True)
public=ROOT/"site/media";public.mkdir(parents=True,exist_ok=True)
demo=Path("/tmp")/("mackit-demo-"+str(os.getpid()));demo.mkdir();home=demo/"home";home.mkdir()
with tarfile.open(ROOT/"dist/releases"/("mackit-v"+version+".tar.gz")) as t:t.extractall(demo,filter="data")
kit=demo/("mackit-v"+version);kit.rename(demo/"kit");kit=demo/"kit"
(home/".zshrc").write_text("# My original shell configuration\n")
env={"HOME":str(home),"PATH":str(kit/"bin")+":/opt/homebrew/bin:/usr/bin:/bin","TERM":"dumb","LANG":"en_US.UTF-8"}
steps=[
("查键与配置","mackit keys 编号"),
("查键与配置","mackit edit nvim-keys --print"),
("预览与安装","mackit plan --components zsh,nvim"),
("预览与安装","mackit apply --components zsh,nvim"),
("预览与安装","mackit doctor --components zsh,nvim"),
("恢复旧配置","mackit restore"),
("恢复旧配置","cat ~/.zshrc")]
latin=ImageFont.truetype("/System/Library/Fonts/Menlo.ttc",22)
cjk=ImageFont.truetype("/System/Library/Fonts/STHeiti Light.ttc",24)
titlefont=ImageFont.truetype("/System/Library/Fonts/STHeiti Light.ttc",26)
def width(c):return 2 if unicodedata.east_asian_width(c) in "WF" else 1
def wrapped(text,columns=86):
 lines=[]
 for raw in text.splitlines():
  line="";n=0
  for char in raw:
   w=width(char)
   if n+w>columns:lines.append(line);line="";n=0
   line+=char;n+=w
  lines.append(line)
 return lines
def drawline(draw,xy,text,color):
 x,y=xy
 for c in text:
  draw.text((x,y),c,font=cjk if width(c)==2 else latin,fill=color)
  x+=13.3*width(c)
records=[];frames=[];offset=0;chapters=[];previous=None
for i,(title,cmd) in enumerate(steps):
 if title!=previous:chapters.append({"title":title,"start":offset});previous=title
 master,slave=pty.openpty()
 fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack("HHHH",40,100,0,0))
 start=time.monotonic()
 proc=subprocess.Popen(["/bin/sh","-c",cmd],stdin=slave,stdout=slave,stderr=slave,env=env,cwd=kit);os.close(slave)
 chunks=[];events=[]
 while True:
  ready,_,_=select.select([master],[],[],.1)
  if ready:
   try:data=os.read(master,65536)
   except OSError:break
   if not data:break
   decoded=data.decode("utf-8",errors="replace");events.append([round(time.monotonic()-start,4),"o",decoded]);chunks.append(decoded)
  if proc.poll() is not None and not ready:break
 os.close(master);proc.wait(timeout=10)
 assert proc.returncode==0,(cmd,"".join(chunks))
 output=re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]","","".join(chunks)).replace("\r","")
 elapsed=time.monotonic()-start;duration=6 if i in [0,2,3,5] else 4
 records.append({"command":cmd,"stdout":output,"exit_code":proc.returncode,"actual_seconds":elapsed,"events":events,"start":offset,"presentation_seconds":duration})
 image=Image.new("RGB",(1280,720),"#eff0e4");draw=ImageDraw.Draw(image)
 draw.rounded_rectangle((24,24,1256,696),radius=16,fill="#20382d")
 for j,color in enumerate(["#d28a71","#d2bd73","#91b480"]):draw.ellipse((48+j*24,46,60+j*24,58),fill=color)
 draw.text((160,39),"Tianli MacKit  /  v"+version,font=latin,fill="#c2d0b5")
 draw.text((48,90),f"{i+1:02d}   {title}",font=titlefont,fill="#c4e396")
 display=wrapped("$ "+cmd)+[""]+wrapped(output.rstrip())
 for n,line in enumerate(display[-17:]):drawline(draw,(48,143+n*27),line,"#e2eedc" if n else "#cae6a7")
 draw.line((48,638,1230,638),fill="#53684e")
 draw.text((48,656),"真实 CLI 输出回放 · 隔离 HOME · 每步增加阅读停留",font=titlefont,fill="#bdcdb2")
 file=work/(f"step-{i+1}.png");image.save(file);frames.append((file,duration));offset+=duration
 if i==0:shutil.copy2(file,public/"terminal.png")
(work/"raw-recording.json").write_text(json.dumps(records,ensure_ascii=False,indent=2))
manifest={"version":version,"recorded_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source":"Real CLI processes captured via PTY in a disposable HOME; replay uses presentation holds, not realtime desktop capture.","chapters":chapters,"duration":offset,"coverage":["key lookup","config source","plan","apply","doctor","restore existing file"],"not_covered":["physical global key delivery","fresh plugin download","GUI permission dialogs"]}
(public/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(public/"transcript.txt").write_text("\n\n".join("$ "+r["command"]+"\n"+r["stdout"] for r in records))
concat=work/"frames.txt";concat.write_text("".join("file '"+str(f)+"'\nduration "+str(d)+"\n" for f,d in frames)+"file '"+str(frames[-1][0])+"'\n")
subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",str(concat),"-vf","fps=24,format=yuv420p","-c:v","libx264","-crf","22","-movflags","+faststart","-t",str(offset),str(public/"tutorial.mp4")],check=True)
def stamp(t):return f"00:{int(t)//60:02d}:{int(t)%60:02d}.000"
(public/"tutorial.vtt").write_text("WEBVTT\n\n"+"\n".join(stamp(r["start"])+" --> "+stamp(r["start"]+r["presentation_seconds"])+"\n"+steps[i][0]+"："+r["command"]+"\n" for i,r in enumerate(records)))
assert (home/".zshrc").read_text()=="# My original shell configuration\n"
print(json.dumps({"duration":offset,"chapters":chapters,"restored_original":True},ensure_ascii=False))

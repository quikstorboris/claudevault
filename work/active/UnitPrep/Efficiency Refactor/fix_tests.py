"""usage: fix_tests.py <orig .rs path in HEAD, e.g. src/api/X.rs> <new dir, e.g. src/api/X>
Rewrites <dir>/tests.rs so its `use super::*;` becomes: the original file's whole `use` block (as it was
in HEAD) + glob imports of every sibling part module. Follow with `cargo fix` to drop what is unused."""
import os,re,subprocess,sys
os.chdir(os.path.expanduser('~/Development/unitprep-api'))
orig,newdir=sys.argv[1],sys.argv[2]
src=subprocess.check_output(['git','show','HEAD:'+orig]).decode()
lines=src.split('\n')
first=next(k for k,l in enumerate(lines) if l.startswith('use '))
k=first;end=first
while k<len(lines):
    if lines[k].startswith('use '):
        j=k
        while not lines[j].rstrip().endswith(';'): j+=1
        end=j;k=j+1
    elif lines[k].strip()=='' or lines[k].startswith('//'): k+=1
    else: break
block='\n'.join(lines[first:end+1])
# crate-internal sibling modules in the new dir
test_files=[f for f in os.listdir(newdir) if f.endswith('tests.rs')]
parts=sorted(f[:-3] for f in os.listdir(newdir) if f.endswith('.rs') and f!='mod.rs' and f not in test_files)
globs='\n'.join('use super::%s::*;'%p for p in parts)
for tf in test_files:
    p=os.path.join(newdir,tf)
    t=open(p).read()
    if 'use super::*;' not in t: continue
    t=t.replace('use super::*;',block+'\n'+globs,1)
    open(p,'w').write(t)
print('ok',test_files)

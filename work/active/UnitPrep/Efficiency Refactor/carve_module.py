"""Generic mechanical splitter: turns src/.../X.rs into src/.../X/{mod.rs, parts...}.

usage: carve.py <rel path of X.rs> <config.json>
config: {"segments": [["name", "regex matching the first line of the segment's first item"], ...],
         "tests": "tests"|null,   # name of the inline `#[cfg(test)] mod tests` -> tests.rs
         "mod_reexports": ["pub use part::name", ...]  # lines for mod.rs
        }
Segments must be in file order. Everything before the first segment (after the use block) stays in mod.rs.
"""
import json,os,re,subprocess,sys
rel,cfgp=sys.argv[1],sys.argv[2]
cfg=json.load(open(cfgp))
root=os.path.expanduser('~/Development/unitprep-api')
os.chdir(root)
srcdir=os.path.dirname(rel); base=os.path.basename(rel)[:-3]
newdir=os.path.join(srcdir,base)
os.makedirs(newdir,exist_ok=True)
subprocess.check_call(['git','mv',rel,os.path.join(newdir,'mod.rs')])
L=open(os.path.join(newdir,'mod.rs')).read().split('\n')

def with_attrs(k):
    while k>0 and (L[k-1].startswith('///') or L[k-1].startswith('#[')): k-=1
    return k
def find(rx,start=0):
    for k in range(start,len(L)):
        if re.search(rx,L[k]): return k
    raise SystemExit('marker not found: '+rx)

# --- leading doc + use block
first_use=next(k for k,l in enumerate(L) if l.startswith('use '))
doc='\n'.join(L[:first_use]).rstrip('\n')
# end of use block: last line that belongs to a `use` statement
k=first_use; last_use_end=first_use
while k<len(L):
    if L[k].startswith('use '):
        j=k
        while not L[j].rstrip().endswith(';'): j+=1
        last_use_end=j; k=j+1
    elif L[k].strip()=='' or L[k].startswith('//'): k+=1
    else: break
use_text='\n'.join(L[first_use:last_use_end+1])

def parse_use(text):
    leaves=[]
    for stmt in re.findall(r'use\s+(.*?);',text,flags=re.S):
        stmt=stmt.strip()
        def walk(prefix,s):
            s=s.strip()
            if '{' not in s:
                path=prefix+s
                name=path.split('::')[-1]
                if ' as ' in name:
                    p,alias=path.split(' as ')
                    leaves.append((p.rsplit('::',1)[0],p.rsplit('::',1)[1],alias.strip()))
                else:
                    leaves.append((path.rsplit('::',1)[0] if '::' in path else '',name,None))
                return
            head,rest=s.split('{',1)
            body=rest.rsplit('}',1)[0]
            depth=0;cur='';items=[]
            for ch in body:
                if ch=='{': depth+=1
                if ch=='}': depth-=1
                if ch==',' and depth==0: items.append(cur);cur=''
                else: cur+=ch
            if cur.strip(): items.append(cur)
            for it in items:
                it=it.strip()
                if it=='self': leaves.append((prefix+head.rstrip(':'),prefix+head.rstrip(':').split('::')[-1] and head.rstrip(':').split('::')[-1],None))
                else: walk(prefix+head,it)
        walk('',stmt)
    return leaves
leaves=parse_use(use_text)

# --- segments
starts=[]
for name,rx in cfg['segments']:
    starts.append((name,with_attrs(find(rx,starts[-1][1]+1 if starts else 0))))
# every inline `#[cfg(test)]\nmod NAME {` block (there may be several, at the end of the file)
test_blocks=[]
if cfg.get('tests'):
    for k in range(len(L)-1):
        if L[k]=='#[cfg(test)]':
            m_=re.match(r'mod (\w+) \{',L[k+1])
            if m_: test_blocks.append((m_.group(1),k))
end_of_items=with_attrs(test_blocks[0][1]) if test_blocks else len(L)
def blk(a,b): return '\n'.join(L[a:b]).strip('\n')+'\n'
parts={}
for i,(name,a) in enumerate(starts):
    b=starts[i+1][1] if i+1<len(starts) else end_of_items
    parts[name]=parts.get(name,'')+blk(a,b)
mod_body=blk(last_use_end+1,starts[0][1])

def vis(text):
    text=re.sub(r'^(fn |async fn |struct |enum |const |type |static )',r'pub(super) \1',text,flags=re.M)
    text=re.sub(r'^    (fn |async fn )',r'    pub(super) \1',text,flags=re.M)  # inherent impl methods
    def fields(m):
        body=re.sub(r'^    (?!pub)(\w+:)',r'    pub(super) \1',m.group(2),flags=re.M)
        return m.group(1)+body+'}'
    text=re.sub(r'(^(?:pub(?:\(super\))? )?struct \w+(?:<[^>]*>)? \{\n)(.*?)^\}',lambda m:fields(m)+'',text,flags=re.S|re.M)
    return text
# impl-trait methods must NOT be pub(super): revert inside `impl Trait for`
def fix_trait_impls(text):
    def repl(m):
        return m.group(0).replace('pub(super) fn ','fn ').replace('pub(super) async fn ','async fn ')
    return re.sub(r'^impl[^\n{]* for [^\n{]*\{\n.*?^\}',repl,text,flags=re.S|re.M)
def vis_all(t): return fix_trait_impls(vis(t))
for n in parts: parts[n]=vis_all(parts[n])
mod_body=vis_all(mod_body)

def top_names(text):
    return set(re.findall(r'^pub\(super\) (?:async )?(?:fn|struct|enum|const|type|static) (\w+)',text,flags=re.M))|set(re.findall(r'^pub (?:async )?(?:fn|struct|enum|const|type|static) (\w+)',text,flags=re.M))
owner={}
for n,t in parts.items():
    for nm in top_names(t): owner[nm]=n
for nm in top_names(mod_body): owner.setdefault(nm,'mod')
def used(body,n): return re.search(r'(?<![\w:])'+re.escape(n)+r'\b',body) is not None
def strip_comments(t): return '\n'.join(l for l in t.split('\n') if not l.strip().startswith('//'))
def header(name,body):
    code=strip_comments(body)
    out_by={}
    for path,leaf,alias in leaves:
        shown=alias or leaf
        hit=used(code,shown)
        if leaf in ('IntoResponse',) : hit=hit or 'into_response' in code
        if hit: out_by.setdefault(path,[]).append(leaf+(' as '+alias if alias else ''))
    extra=[]
    # traits used by method call only
    for tr,probe in [('IntoResponse','.into_response()')]:
        pass
    lines=[]
    for path,ns in out_by.items():
        ns=sorted(set(ns))
        lines.append('use '+path+'::{'+', '.join(ns)+'};' if len(ns)>1 else 'use '+path+'::'+ns[0]+';')
    # sibling items
    sib={}
    for nm,o in owner.items():
        if o==name: continue
        if used(code,nm):
            sib.setdefault(o,[]).append(nm)
    for o,ns in sorted(sib.items()):
        target='super' if o=='mod' else 'super::'+o
        lines.append('use '+target+'::{'+', '.join(sorted(ns))+'};' if len(ns)>1 else 'use '+target+'::'+ns[0]+';')
    return '\n'.join(lines)+('\n' if lines else '')
for n,t in parts.items():
    open(os.path.join(newdir,n+'.rs'),'w').write(('//! '+cfg.get('docs',{}).get(n,n)+'\n\n') + header(n,t)+'\n'+t)
tests_mod=''
for bi,(tname,tstart) in enumerate(test_blocks):
    # doc comments above a test module's `#[cfg(test)]` belong to THAT module (they become `//!`)
    tstart=with_attrs(tstart) if bi>0 or True else tstart
    tend=with_attrs(test_blocks[bi+1][1]) if bi+1<len(test_blocks) else len(L)
    t=blk(tstart,tend)
    pre=[]
    while t.startswith('///'):
        first_line,t=t.split('\n',1)
        pre.append('//!'+first_line[3:])
    t=t.replace('#[cfg(test)]\n','',1)
    t=re.sub(r'^mod \w+ \{\n','',t,count=1)
    t=t.rstrip()
    assert t.endswith('}')
    t=t[:-1].rstrip()
    t='\n'.join(l[4:] if l.startswith('    ') else l for l in t.split('\n'))
    open(os.path.join(newdir,tname+'.rs'),'w').write(('\n'.join(pre)+'\n\n' if pre else '')+t+'\n')
    tests_mod+='#[cfg(test)]\nmod '+tname+';\n'
mods=''.join('mod '+n+';\n' for n in dict.fromkeys(n for n,_ in starts))
reex='\n'.join(cfg.get('mod_reexports',[]))+'\n' if cfg.get('mod_reexports') else ''
modrs=doc+'\n\n'+mods+tests_mod+'\n'+reex+'\n'+header('mod',mod_body)+'\n'+mod_body
open(os.path.join(newdir,'mod.rs'),'w').write(modrs)
print('carved',rel,'->',newdir,[ (n,len(t.split(chr(10)))) for n,t in parts.items()])

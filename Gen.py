"""
mixi の日記+コメント+画像データをダウンロードする方法

(1)
mixi export
https://adiary.org/download/tools/mixi_export.html
で mixi の日記データを全部ダウンロード
perl mixi_export.pl
→adiary.xmlが生成される

(2)
adiary.xml と同じディレクトリにて以下を実行。
python3 Gen.py
生成されるもの:
- posts.json ... adiary.xml よりもうちっとシンプルな構造のファイル。データ構造は parse 関数のところを参照。
- download_images.sh ... 日記中の画像を images/ にダウンロードするシェルスクリプト
- diary.html ... posts.json から生成した超簡素な日記とコメント一覧。

(3)
画像をダウンロード
sh download_images.sh

"""

import sys
import json
import re
import os, datetime
import xml.etree.ElementTree as ET

def t2s(timestamp):
	"""
	Return localtime string
	timestamp: number (unixtime in sec)
	"""
	d = datetime.datetime.fromtimestamp(timestamp)
	return "%04d-%02d-%02d_%02d:%02d:%02d.%03d" % (d.year, d.month, d.day, d.hour, d.minute, d.second, d.microsecond//1000)

def toNative(e):
	return {
		"tag": e.tag,
		"attr": dict(e.items()),
		"text": rmNone(e.text),
		"tail": rmNone(e.tail),
		"children": [ toNative(ce) for ce in list(e) ],
	}

def get(d, tag, default):
	es = [ e for e in d["children"] if e["tag"]==tag ]
	if len(es):
		return es[0]
	return default

def parseComment(d):
	def f(k, v):
		if k=="timestamp":
			return k, int(v)
		return k, v
	ks = [
		("username", "username"),
		("timestamp", "timestamp"),
		("body", "text"),
	]
	return dict([ f(dstK, get(d, srcK, "")["text"]) for srcK, dstK in ks ])

def rmNone(s):
	return "" if s is None else s

def contentString(e, isRoot=True):
	ch = "".join([contentString(c, isRoot=False) for c in e.get("children", [])])
	if isRoot:
		return e["text"]+ch
	else:
		attrs = " ".join([ k+"='"+v+"'" for k, v in e["attr"].items() ])
		return "<"+e["tag"]+" "+attrs+">"+e["text"]+ch+e["tail"]+"</"+e["tag"]+">"

def parseDay(d):
	t = int(get(d, "attributes", {}).get("attr", {}).get("tm", "0"))
	text = contentString(get(d, "body", {}))
	assert text is not None, d
	comments = [ parseComment(e) for e in get(d, "comments", {}).get("children", []) ]
	return {
		"timestamp": t,
		"text": text,
		"comments": comments,
	}

def parse(d):
	"""
	return Post[]
	Post: Dict
		timestamp: int
		text: string
		comments: Comment[]
	Comment: Dict
		timestamp: int
		username: string
		text: string
	"""
	return [ parseDay(e) for e in d["children"] ]

def gen_download_sh(posts):
	g = {"reps": {}}
	def extractImages(s):
		uris = re.findall(r'https?://.*?\.(?:jpg|gif)', s)
		return [ uri.replace("<wbr />", "") for uri in uris ]
	def dl(uri):
		_, ext = os.path.splitext(uri)
		idx = len(g["reps"])
		f = "images/{idx:06d}{ext}".format(**vars())
		g["reps"][uri] = f
		return "sleep 1; curl {uri} > {f}".format(**vars())
	uris = list(sorted(set(sum([ extractImages(e["text"]) for e in posts ], []))))
#	print(uris)
	with open("download_images.sh", "w") as f:
		print("mkdir -p images", file=f)
		print("\n".join([ dl(uri) for uri in uris ]), file=f)
	# 本文の置き換え
	for post in posts:
		for s, d in g["reps"].items():
			post["text"] = post["text"].replace(s, d)

def render(posts):
	def renderComment(c):
		return "COMMENT: "+t2s(c["timestamp"])+" "+c["username"]+": "+c["text"]
	def renderPost(post):
		cs = "<br>".join([ renderComment(c) for c in post["comments"] ])
		return "<div>DIARY: "+t2s(post["timestamp"])+"<br>"+post["text"].replace("\n", "<br>")+"<br>"+cs+"</div>"
	s = "<br>\n".join([renderPost(p) for p in posts])
	with open("diary.html", "w") as f:
		print(s, file=f)

def process(xml_filename):
	tree = ET.parse(xml_filename)
	root = tree.getroot()
	dn = toNative(root)
	posts = parse(dn)
	gen_download_sh(posts)
#	print(json.dumps(dn, indent=4))
	with open("posts.json", "w") as f:
		print(json.dumps(posts, indent=4), file=f)
	render(posts)



process("adiary.xml")


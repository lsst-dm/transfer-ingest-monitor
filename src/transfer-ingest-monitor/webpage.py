import sqlite3

def db_to_html(db, query, linkify=False, modifier=''):
    if isinstance(query,str):
      query=[query]
    conn = sqlite3.connect(db)
    html='<table style="width:100%">\n'
    c = conn.cursor()
    c.execute(query[0])
    columns= [description[0] for description in c.description]
    td='</td><td>'
    tdl='</td><td style="border-left:2px dashed silver;">'
    btd='</b></td><td><b>'
    hstring='<thead><tr style="border-top:3px solid black; border-bottom:3px solid black;"><td><b>'
    for column in columns:
        hstring+=column.replace('_',' ')+btd
    hstring += '</b></td></tr></thead>\n'
    html += hstring
    rows=c.fetchall()
    for num in range(1,len(query)):
        c.execute(query[num])
        rows.extend(c.fetchall())

    printhnum=20
    rownum=0
    for row in rows:
       if rownum == printhnum:
           html += hstring
           rownum=0
       rownum+=1
       html+='<tr style="border-bottom:2px dashed silver;"><td>'
       datanum=0
       for data in row:
           if (datanum == 0 ) & (linkify):
              html+='<a href="'+str(data)+modifier+'.html">'+str(data)+'</a>'+tdl
           else:
              html+=str(data)+tdl
           datanum+=1
       html+='</tr>\n'
    html+='</table>\n'
    return html

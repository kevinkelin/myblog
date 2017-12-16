#coding:gbk

import netutilex,os

flist = netutilex._listFile_(os.getcwd())


for i in flist:
    try:
        if '2011' in i or '2012' in i or '2013' in i or '2014' in i or '2015' in i:
            if '_thumb' not in i:
                print i
                newname = "%s_thumb%s"%(os.path.splitext(os.path.basename(i))[0],os.path.splitext(os.path.basename(i))[1])
                print newname
                os.system('copy "%s" "%s"'%(i,os.path.join(os.path.dirname(i),newname)))
                
    except Exception as e:
        print e
        
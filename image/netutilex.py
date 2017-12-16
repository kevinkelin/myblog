#coding:gbk
"""
netutilex
"""
import paramiko
import sys, os, re, stat
import win32file, win32con, win32gui
import ctypes
import ftplib
import threading
import Queue
import socket
socket.setdefaulttimeout(60)

STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE= -11
STD_ERROR_HANDLE = -12

FOREGROUND_WHITE = 0x0007
FOREGROUND_BLUE = 0x01 # text color contains blue.
FOREGROUND_GREEN= 0x02 # text color contains green.
FOREGROUND_RED  = 0x04 # text color contains red.
FOREGROUND_INTENSITY = 0x08 # text color is intensified.
FOREGROUND_YELLOW = FOREGROUND_RED | FOREGROUND_GREEN

BACKGROUND_BLUE = 0x10 # background color contains blue.
BACKGROUND_GREEN= 0x20 # background color contains green.
BACKGROUND_RED  = 0x40 # background color contains red.
BACKGROUND_INTENSITY = 0x80 # background color is intensified.

def _listFile_(path, isDeep=True):
    flist = []
    if not os.path.exists(path) or not os.path.isdir(path):
        return flist
    if isDeep:
        for root, dirs, files in os.walk(path):
            for fl in files:
                flist.append('%s\%s' % (root, fl))
    else:
        flles = os.listdir(path)
        for fl in flles:
            fl = '%s\%s' % (path, fl)
            if os.path.isfile(fl):
                flist.append(fl)
    return flist

def _listDir_(path, isDeep=True):
    dlist = []
    if not os.path.exists(path) or not os.path.isdir(path):
        return dlist
    if isDeep:
        for root, dirs, files in os.walk(path):
            for dl in dirs:
                dlist.append('%s\%s' % (root, dl))
    else:
        dirs = os.listdir(path)
        for dl in dirs:
            dl = '%s\%s' % (path, dl)
            if os.path.isdir(dl):
                dlist.append(dl)
    return dlist

class PRINT():
    def __init__(self):
        self.handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

    def __set_color__(self, color):
        return ctypes.windll.kernel32.SetConsoleTextAttribute(self.handle, color)

    def __print__(self, data, color):
        self.__set_color__(color)
        sys.stdout.write(data+'\n')
        sys.stdout.flush()
        self.__set_color__(FOREGROUND_WHITE)

    def white(self, data):
        self.__print__(data, FOREGROUND_WHITE|FOREGROUND_INTENSITY)

    def blue(self, data):
        self.__print__(data, FOREGROUND_WHITE|FOREGROUND_INTENSITY)

    def red(self, data):
        self.__print__(data, FOREGROUND_RED|FOREGROUND_INTENSITY)

    def green(self, data):
        self.__print__(data, FOREGROUND_GREEN|FOREGROUND_INTENSITY)

    def yellow(self, data):
        self.__print__(data, FOREGROUND_YELLOW|FOREGROUND_INTENSITY)

    
class SFTP():
    def __init__(self, prefix, user, pswd, port=22):
        self.prefix = prefix
        self.user = user
        self.pswd = pswd
        self.port = port
        self.sftp, self.ssh = self.open()

        # use for callback
        self.s_s = r'-\|/'
        self.s_count = 0
        self.callback = False

        # use for std print
        self.log = PRINT()
        
    def open(self):
        try:
            ssh=paramiko.Transport((self.prefix, self.port))
            ssh.connect(username=self.user, password=self.pswd)
            sftp=paramiko.SFTPClient.from_transport(ssh)
            return sftp, ssh
        except:
            return None, None

    def close(self):
        try:
            if self.sftp: self.sftp.close()
        except:
            pass
        try:
            if self.ssh: self.ssh.close()
        except:
            pass

    # 重连
    def reconect(self):
        if not self.isSftpAlive():
            self.close()
            self.sftp, self.ssh = self.open()

    # 判断sftp是否还活着            
    def isSftpAlive(self):
        try:
            if not self.sftp or not self.ssh:
                return False
            if not self.sftp.sock:
                return False
            if self.isSftpDir('/'):
                return True
        except Exception, e:
            print e
            pass

        
    # 获取 callback
    def getCallBack(self):
        callback = None
        if self.callback:
            callback = self.__myCallback__
        return callback


    # 回调函数
    def __myCallback__(self, size, file_size):
        if size == file_size:
            sys.stdout.write('\b\b\b\b\b\b\b\b' + '传输完成...\r\n')
            return
        persent = (float(size)/file_size)*100
        sys.stdout.write('\b\b\b\b\b\b' + self.s_s[self.s_count] + ' %0.0f' % persent + '%')
        self.s_count = (self.s_count+1)%4


    # 获得sftp指定文件 (大小，修改时间)
    def getSftpAttr(self, src):
        try:
            statues = self.sftp.stat(src)
            return (statues.st_size, statues.st_mtime)
        except Exception, e:
            pass

    # 获得指定路径在sftp上真实路径
    def getSftpRealName(self, src):
        pathlist = os.path.normpath(src).split('\\')
        path = None
        for i in range(len(pathlist)-1):
            if not path:
                fl = self.sftp.listdir('/')
            else:
                fl = self.sftp.listdir(path)
            existed = False
            for name in fl:
                if type(name) == unicode:
                    name = name.encode('utf8')
                if name.lower() == pathlist[i+1].lower():
                    if path:
                        path = path + '/' + name
                    else:
                        path = '/' + name
                    existed = True
            if not existed:
                return
        return path


    # 判断指定路径是否是sftp有效路径
    def isSftpDir(self, src):
        try:
            return stat.S_ISDIR(self.sftp.stat(src).st_mode)
        except Exception, e:
            pass


    # 判断指定路径是否是sftp有效文件
    def isSftpFile(self, src):
        try:
            return stat.S_ISREG(self.sftp.stat(src).st_mode)
        except:
            pass


    # 返回指定路径文件真实名称            
    def genSftpFileExists(self, src):
        try:
            ret =  self.isSftpFile(self.sftp, src)
            if ret:
                return src
            real = self.getSftpRealName(self.sftp, src)
            if  real:
                return real
        except Exception, e:
            self.log.red('sftp:genSftpFileExists '+str(e))


    # 同步sftp目录 或 文件
    # remotepath : 目录或者文件
    # locatepath : 本地目录(不存在自动创建)
    def syncSftpDir(self, remotepath, locatepath, isDeep=True, filter=None):
        _remotepath = self.getSftpRealName(remotepath)
        if _remotepath:
            try:
                flag = True
                if self.isSftpDir(_remotepath):
                    dirlist, filelist = self.listSftp(_remotepath, isDeep)
                    for x in filelist:
                        if filter:
                            if not os.path.splitext(x)[1].lower() in filter:
                                continue
                        ret = self.syncSftpFile(x, locatepath+'\\'+x[len(_remotepath)+1:].replace('/', '\\'))
                        if not ret:
                            flag = False
                    return flag
                else:
                    return self.syncSftpFile(_remotepath, locatepath)
            except Exception, e:
                self.log.red('sftp:syncSftpDir '+str(e))
        else:
            self.log.red('sftp:syncSftpDir %s不存在' % remotepath)


    # 同步sftp文件
    # remotepath : 远程文件名
    # locatepath : 本地文件
    def syncSftpFile(self, remotefile, locatefile):
        lpath = os.path.dirname(locatefile)
        if not os.path.exists(lpath):
            cmd = 'mkdir "%s" >NUL 2>NUL' % lpath
            os.system(cmd)
        self.getSftpData(remotefile, locatefile, False)
        ret = self.verifySftpFile(remotefile, locatefile)
        if not ret:
            self.getSftpData(remotefile, locatefile, False)
        ret = self.verifySftpFile(remotefile, locatefile)
        return ret


    # 校验sftp上目录与本地目录中文件的一致性
    # remotepath : 远程目录
    # locatepath : 本地目录
    def verifySftpDir(self, remotepath, locatepath, isDeep=True):
        _dic = {}
        try:
            dirlist, filelist = self.listSftp(remotepath, isDeep)
            for x in filelist:
                ret = self.verifySftpFile(x, locatepath+'\\'+x[len(remotepath)+1:].replace('/', '\\'))
                _dic[x] = ret
            return _dic
        except Exception, e:
            self.log.red('sftp:verifyStfpDir '+str(e))


    # 内部函数
    # 校验|设置 sftp上文件与本地文件一致性，
    # remotefile : 远程文件
    # locatefile : 本地文件名
    # isSet : 是否同步本地文件mtime
    def verifySftpFile(self, remotefile, locatefile, isSet=True):
        try:
            lsize, rsize, lmtime, rmtime = -1, -1, -1, -1
            if os.path.isdir(locatefile):
                locatefile = os.path.join(locatefile, os.path.basename(remotefile))

            res = self.getSftpAttr(remotefile)
            if not res:
                return False
            rsize, rmtime = res

            if isSet:        
                handle = win32file.CreateFile(locatefile, win32file.GENERIC_WRITE, 0, None, win32con.OPEN_EXISTING, 0, None)
                win32file.SetFileTime(handle, None, None, rmtime)
                handle.Close()
            
            lsize = os.path.getsize(locatefile)
            lmtime = os.path.getmtime(locatefile)
            
            if lsize != rsize or abs(lmtime - rmtime) > 3:
                return False
            else:
                return True
        except Exception, e:
            self.log.red('sftp:verifySftpFile %s '%remotefile+str(e))


    # 内部函数
    def getSftpData(self, remotepath, local, isDeep=True):
        callback = self.getCallBack()
        try:
            if self.isSftpDir(remotepath):
                dirlist, filelist = self.listSftp(remotepath, isDeep, True)
                for _d in dirlist:
                    lpath = local + '\\' + _d[len(remotepath)+1:].replace('/', '\\')
                    cmd = 'mkdir "%s" >NUL 2>NUL' % lpath
                    os.system(cmd)
                for _f in filelist:
                    lfname = local + '\\' + _f[len(remotepath)+1:].replace('/', '\\')
                    if os.path.exists(lfname):
                        if not self.verifySftpFile(_f, lfname):
                            self.sftp.get(_f, lfname, callback)
                    else:
                        self.sftp.get(_f, lfname, callback)
            else:
                if os.path.isdir(local):
                    local = local + '\\' + os.path.basename(remotepath)
                if os.path.exists(local):
                    if not self.verifySftpFile(remotepath, local):
                        self.sftp.get(remotepath, local, callback)
                else:
                    self.sftp.get(remotepath, local, callback)
        except Exception, e:
            self.log.red('sftp:getSftpData %s '%remotepath+str(e))
            

    # 同步 本地文件与sftp上文件mtime
    # remotefile : 远程文件
    # locatefile : 本地文件名
    def syncSftpTime(self, remotefile, locatefile):
        try:
            if os.path.exists(locatefile):
                rmtime = self.sftp.stat(remotefile).st_mtime
                handle = win32file.CreateFile(locatefile, win32file.GENERIC_WRITE, 0, None, win32con.OPEN_EXISTING, 0, None)
                win32file.SetFileTime(handle, None, None, rmtime)
                handle.Close()
                return True
        except Exception, e:
            self.log.red('sftp:syncSftpTime '+str(e))

    
    # 遍历sftp目录, 返回 {文件名:mtime}
    def listSftpDir(self, remotepath, isDeep=False):
        _dic = {}
        try:
            dirlist, filelist = self.listSftp(remotepath, isDeep)
            for x in dirlist:
                _dic[x] = self.sftp.stat(x).st_mtime
            return _dic
        except Exception, e:
            self.log.red('sftp:listSftpDir '+str(e))
            return {}

    # 遍历sftp目录, 返回dirlist, filelist
    def listSftp(self, remotepath, isDeep=True, topdown=False):
        dirlist, filelist = [], []
        if self.isSftpDir(remotepath):
            if isDeep:
                for root, dirs, files in self.walkSftp(remotepath, topdown):
                    for d in dirs:
                        if type(d) == unicode:
                            d = d.encode('utf8')
                        dirlist.append(root + '/' + d)
                    for f in files:
                        filelist.append(root + '/' + f)
            else:
                dirlist, filelist = self.__listSftp(remotepath, isDeep)
            return dirlist, filelist
        else:
            self.log.yellow('warning:listSftp not a vaild remotepath %s' % remotepath)
            return [], []


    # 内部函数        
    def __listSftp(self, top, flag=True):
        dirlist, filelist = [], []
        for f in self.sftp.listdir_attr(top):
            if not flag:
                fname = top + '/' + f.filename
            else:
                fname = f.filename
            res = re.match(r'^d', f.longname)
            if res:
                dirlist.append(fname)
            else:
                filelist.append(fname)
        return dirlist, filelist

    
    # 内部函数
    # topdown True : 从外到里； False : 从里到外
    def walkSftp(self, top, topdown=True):
        dirlist, filelist = self.__listSftp(top)
        if topdown:
            yield top, dirlist, filelist
        for name in dirlist:
            if type(name) == unicode:
                name = name.encode('utf8')
            path = top + '/' + name
            for x in self.walkSftp(path, topdown):
                yield x
        if not topdown:
            yield top, dirlist, filelist            


    # 上传文件
    def putSftpData(self, locatefiles, remotepath, isTips=False):
        callback = self.getCallBack()
        try:
            for lfname in locatefiles:
                fname = os.path.basename(lfname)
                rpath = remotepath + '/' + fname
                if not self.isSftpDir(remotepath):
                    self.makeSftpDir(remotepath)
                if self.isSftpFile(rpath) and isTips:
                    self.log.yellow('远程服务器存在同名文件...')
                    ret = win32gui.MessageBox(None, '服务器存在同名文件%s' % fname, '覆盖远程服务器文件', 4)
                    if ret == 6:
                        times = (os.path.getatime(lfname), os.path.getmtime(lfname))
                        self.sftp.put(lfname, rpath, callback)
                        self.sftp.utime(rpath, times)
                    else:
                        self.log.yellow('放弃上传...')
                else:
                    res = self.getSftpAttr(rpath)
                    if res:
                        _size, _mtime = res
                        if _size == os.path.getsize(lfname) and _mtime == os.path.getmtime(lfname):
                            continue
                    times = (os.path.getatime(lfname), os.path.getmtime(lfname))
                    self.sftp.put(lfname, rpath, callback)
                    self.sftp.utime(rpath, times)
            return True
        except Exception, e:
            self.log.red('sftp:putSftpData '+str(e))


    def putSftpDir(self, locatedirs, remotepath, isTips=False):
        try:
            pathmap = {}
            for ldir in locatedirs:
                for f in _listFile_(ldir):
                    rpath = remotepath + '/' + os.path.dirname(f)[len(ldir)+1:].replace('\\', '/')
                    pathmap.setdefault(rpath, []).append(f)
            for rpath in pathmap.keys():
                self.putSftpData(pathmap[rpath], rpath, isTips)
        except Exception, e:
            self.log.red('sftp:putSftpDir '+str(e))


    def makeSftpDir(self, remotepath):
        try:
            pathlist = os.path.normpath(remotepath).split('\\')
            path = ''
            for x in pathlist:
                if len(x) > 0:
                    path += '/' + x
                    try:
                        self.sftp.listdir(path)
                    except:
                        self.sftp.mkdir(path)
        except Exception, e:
            self.log.red('sftp:makeSftpDir '+str(e))
        
    def cleanSftpDir(self, remotepath, isDeep=True):
        dirlist, filelist = [], []
        try:
            if self.isSftpDir(remotepath):
                if isDeep:
                    for root, dirs, files in self.walkSftp(remotepath, False):
                        for d in dirs:
                            dirlist.append(root + '/' + d)
                        for f in files:
                            filelist.append(root + '/' + f)
                    for x in filelist:
                        self.sftp.remove(x)
                    for x in dirlist:
                        self.sftp.rmdir(x)
                else:
                    for f in self.listdir_attr(remotepath):
                        res = re.match(r'^d', f.longname)
                        if res:
                            dirlist.append(f.filename)
                        else:
                            filelist.append(f.filename)
                    for x in filelist:
                        self.sftp.remove(remotepath + '/' + x)
        except Exception, e:
            self.log.red('sftp:cleanSftpDir '+str(e))


'ftp client'
class FTP():
    def __init__(self, host, user, pswd, port=21, timeout=30):
        self.host = host
        self.user = user
        self.pswd = pswd
        self.port = port
        self.ftp = self.open()

        self.blocksize = 10*1024*1024 # 10MB        

        # use for callback
        self.s_s = r'-\|/'
        self.s_count = 0
        self.callback = False
        
    def open(self):
        try:
            ftp_client = ftplib.FTP()
            ftp_client.connect(self.host, self.port, self.timeout)
            ftp_client.login(self.username, self.passwd)
            return ftp_client
        except:
            pass

    def close(self):
        try:
            if self.ftp:
                self.ftp.quit()
        except:
            pass
        
    def reconect(self):
        if not self.isFtpAlive():
            self.close()
            self.ftp = open()

    # 获取 callback
    def getCallBack(self):
        callback = None
        if self.callback:
            callback = self.__myCallback__
        return callback

    # 回调函数
    def __myCallback__(self, size, file_size):
        if size == file_size:
            sys.stdout.write('\b\b\b\b\b\b\b\b' + '传输完成...\r\n')
            return
        persent = (float(size)/file_size)*100
        sys.stdout.write('\b\b\b\b\b\b' + self.s_s[self.s_count] + ' %0.0f' % persent + '%')
        self.s_count = (self.s_count+1)%4
        
    def isFtpAlive(self):
        try:
            if not self.ftp:
                return False
            if not self.ftp.sock:
                return False
            if self.ftp.pwd():
                return True
        except:
            pass
        
    def isFtpFile(self, src):
        resp = self.ftp.sendcmd('STAT ' + src)
        if resp[:3] == '213':
            s = resp[3:].strip()
            res = re.search('ftpd:', s, re.DOTALL)
            if res:
                return False
            else:
                return True
            
    def isFtpDir(self, src):
        resp = self.ftp.sendcmd('STAT ' + src)
        if resp[:3] == '212':
            return True
        else:
            return False

    def getFtpFileSize(self, src):
        if self.isFtpFile(src):
            attr = []
            self.ftp.retrlines("LIST "+src, attr.append)
            return int(attr[0].split()[4])
        else:
            return -1

    ##def _splitFile(fname, num=3):
    ##    _l = []
    ##    fsize = os.path.getsize(fname)
    ##    if fsize > FTP_MIN_FILESIZE:
    ##        _size = fsize / num
    ##        for x in range(num):
    ##            _filename = fname + '.%06d' % x
    ##            if x != num - 1:
    ##                _l.append((_filename, _size))
    ##            else:
    ##                _l.append((_filename, fsize-_size*(num-1)))
    ##        curpoint = 0
    ##        sfp = open(fname, 'rb')
    ##        for x in _l:
    ##            fp = open(x[0], 'wb')
    ##            sfp.seek(curpoint)
    ##            data = sfp.read(x[1])
    ##            fp.write(data)
    ##            curpoint += x[1]
    ##            fp.close()
    ##        sfp.close()
    ##        return _l
    ##    else:
    ##        return [(fname,fsize)]

    def syncFtpFileData(self, rfname, lfname):
        if os.path.exists(lfname):
            lsize = os.path.getsize(lfname)
            rsize = self.getFtpFileSize(rfname)
            if lsize != rsize:
                return self.getFtpFileData(rfname, lfname)
            else:
                return True
        else:
            return self.getFtpFileData(rfname, lfname)
            
    def getFtpFileData(self, rfname, lfname):
        rdir = os.path.dirname(rfname)
        self.ftp.cwd(rdir)
        ldir = os.path.dirname(lfname)
        if not os.path.exists(ldir):
            os.system('mkdir "%s"' % ldir)
        fname = os.path.basename(lfname)
        if len(fname) == 0:
            fname = os.path.basename(rfname)
        fname = ldir + '\\' + fname
        cmd = 'RETR ' + rfname
        ret = self.ftp.retrbinary(cmd, open(fname, 'wb').write)
        if ret[:3] == '226':
            return True
        else:
            return False

    # lfname: if path endswith \
    def getFtpData(self, rfname, lfname):
        if self.isFtpDir(rfname):
            flag = True
            dlists, flists = self.listFtp(rfname)
            for x in flists:
                lpath = lfname + '\\' + x[len(rfname):]
                lpath = lpath.replace('/', '\\').replace('\\\\', '\\')
                ret = self.syncFtpFileData(x, lpath)
                if not ret:
                    flag = Flase
            return flag
        elif self.isFtpFile(rfname):
            return self.syncFtpFileData(rfname, lfname)
        else:
            return False

    def putFtpFileData(self, lfname, rfname):
        callback = self.getCallBack()
        rdir = os.path.dirname(rfname)
        self.makeFtpDir(rdir)
        self.ftp.cwd(rdir)
        fname = os.path.basename(rfname)
        if len(fname) == 0:
            fname = os.path.basename(lfname)
        cmd = 'STOR %s' % fname
        fp = open(lfname, 'rb')
        ret = self.ftp.storbinary(cmd, fp, self.blocksize, callback)
        fp.close()
        if ret[:3] == '226':
            return True
        else:
            return False

    # rfname: if path endswith \
    def putFtpData(self, lfname, rfname):
        if not os.path.exists(lfname):
            return False
        if os.path.isdir(lfname):
            flag = True
            lpath = _listFile_(lfname)
            for x in lpath:
                rpath =  (rfname + x[len(lfname)+1:]).replace('\\', '/')
                ret = self.putFtpFileData(x, rpath)
                if not ret:
                    flag = Flase
            return flag
        else:
            return self.putFtpFileData(lfname, rfname)
        
    def makeFtpDir(self, rpath):
        rl = os.path.normpath(rpath).split('\\')
        path = ''
        for x in rl:
            path += '/' + x
            try:
                self.ftp.mkd(path)
            except:
                pass

    def cleanFtpDir(self, rpath):
        if not self.isFtpDir(rpath):
            return False
        dl, fl = self.listFtp(rpath)
        for x in fl:
            self.ftp.delete(x)
        for x in dl:
            self.ftp.rmd(x)
        self.ftp.rmd(rpath)

    # topdown True： 从外到里； False： 从里到外
    def walkftp(self, top, topdown=True):
        dirlist, filelist = self._listFtp(top)
        if topdown:
            yield top, dirlist, filelist
        for name in dirlist:
            path = top + '/' + name
            for x in self.walkftp(path, topdown):
                yield x
        if not topdown:
            yield top, dirlist, filelist

    def _listFtp(self, top, flag=True):
        dirlist, filelist, attr = [], [], []
        self.ftp.retrlines("LIST "+top, attr.append)
        for f in attr:
            if re.search(r"^total", f):
                continue
            l = re.split('\s+', f, 8)
            ftype, fname = l[0], l[8]
            if not flag:
                fname = (top + '/' + fname).replace('//', '/')
            res = re.match(r'^d', ftype)
            if res:
                dirlist.append(fname)
            else:
                filelist.append(fname)
        return dirlist, filelist

    def listFtp(self, remotepath, isDeep=True, topdown=False):
        if self.isFtpDir(remotepath):
            dirlist, filelist = [], []
            if isDeep:
                for root, dirs, files in self.walkftp(remotepath, topdown):
                    for d in dirs:
                        fname = (root + '/'+ d).replace('//', '/')
                        dirlist.append(fname)
                    for f in files:
                        fname = (root + '/'+ f).replace('//', '/')
                        filelist.append(fname)
            else:
                dirlist, filelist = self._listFtp(remotepath, isDeep)
            return dirlist, filelist
        else:
##            _print('warning:listFtp not a vaild remotepath %s' % remotepath, FOREGROUND_YELLOW|FOREGROUND_INTENSITY)
            return [], []

## http session

class WorkerManager:   
    def __init__(self, num_of_workers=10, timeout = 1):   
        self.workQueue = Queue.Queue()   
        self.resultQueue = Queue.Queue()   
        self.threads = []   
        self.timeout = timeout   
        self._recruitThreads(num_of_workers)
        
    def _recruitThreads(self, num_of_workers):   
        for i in range(num_of_workers):   
            thread = Worker(self.workQueue, self.resultQueue, self.timeout)   
            self.threads.append(thread)
            
    def wait_for_complete(self):   
        while len(self.threads):   
            thread = self.threads.pop()   
            thread.join( )   
            if thread.isAlive() and not self.workQueue.empty():   
                self.threads.append(thread)   
        
    def add_job(self, callable, *args, **kwds ):   
        self.workQueue.put((callable, args, kwds))
        
    def get_result(self, *args, **kwds):   
        return self.resultQueue.get(*args, **kwds)
     
class Worker(threading.Thread):
    def __init__( self, workQueue, resultQueue, timeout = 0, **kwds):   
        threading.Thread.__init__( self, **kwds )   
        self.setDaemon(True)   
        self.workQueue = workQueue   
        self.resultQueue = resultQueue   
        self.timeout = timeout   
        self.start()
        
    def run( self ):   
        while True:   
            try:   
                callable, args, kwds = self.workQueue.get(timeout=self.timeout)   
                res = callable(*args, **kwds)   
                self.resultQueue.put(res)   
            except Queue.Empty:   
                break   
            except:
                _print('Worker: %s %s %s' % sys.exc_info(), FOREGROUND_RED|FOREGROUND_INTENSITY)
 
            
def http_downloader(url, fname, isForce=True, retry_count=5):
    # 下载线程数
    worker_num = 8
    block = 2*1024*1024 #1MB

    res = re.match(r'^http\:\/\/(.*?)\/(.*?)$', url)
    if res:
        host, selector = res.groups()
        return getFileMutiThread(fname, fname, host, selector, worker_num, block, isForce, retry_count)
            
def download_job(fname, host, selector, begin, end):
    retry = 5
    url = r'http://' + host + selector
    head = getHttpDataRange(host, selector, begin, end, isForce=False)
    data = getHttpData(url, head)
    while retry:
        if retry != 5:
            time.sleep(10)
        retry -= 1
        if not data:
            head = getHttpDataRange(host, selector, begin, end, isForce=True)
            data = getHttpData(url, head)
        else:
            break
    result = {}
    result[fname] = data
    return result

def getFileMutiThread(fname, host, selector, worker_num, block, isForce=True, retry_count=5):
    print fname, host, selector
    dlen, retry,  flag = None, 0, False
    while True:
        if retry:
            flag = True
        try:
            dlen = getHttpDataLength(host, selector, flag)
        except Exception, e:
            dlen = 0
        if not dlen:
            retry += 1
            if retry == retry_count:
                _print('getFileMutiThread:文件没找到,达到重试限制...%s' % fname, FOREGROUND_RED|FOREGROUND_INTENSITY)
                return False
            else:
                _print('getFileMutiThread:文件没找到,30秒后重试...%s' % fname, FOREGROUND_RED|FOREGROUND_INTENSITY)
                time.sleep(30)
        else:
            break
    if int(dlen) < block:
        block_num = 1
    else:
        block_num = int(dlen)/block
    print block_num
    if os.path.exists(fname):
        if str(os.path.getsize(fname)) == dlen and not isForce:
            return True
    # 分块
    d_range = getMutiLenList(dlen, block_num)

    # 归并文件    
    filelist = {}
    data = ''

    # 线程池
    wm = WorkerManager(worker_num)
    for i in range(len(d_range)):
        (start, end) = d_range[i]
        tmp = '%08d%08d%08d%08d' % (random.randint(1, 100000000), random.randint(1, 100000000), random.randint(1, 100000000), random.randint(1, 100000000))
        d_f = '%s\\__%03d__%s_%s' % (os.path.split(fname)[0], i, tmp, os.path.split(fname)[1])
        wm.add_job(download_job, d_f, host, selector, start, end)
    wm.wait_for_complete()

    while wm.resultQueue.qsize():
        filelist.update(wm.resultQueue.get())

    for x in sorted(filelist.keys()):
        print x
        if not filelist[x]:
            return False
        data += filelist[x]

    if int(dlen) != int(len(data)):
        return False
    else:
        setFileData(fname, data, 'wb')
        return True

if __name__=='__main__':
    print _listFile_(r'd:', False)
##    obj = SFTP('10.16.20.38', 'qihoo', 'qihoo.net')
##    obj.callback = True
##    print obj.isSftpAlive()
##    obj.putSftpDir([r'F:\WorkFlow\20111021'], '/g-qa-new/personal/zhangjie/tsa')
##    obj.makeSftpDir('/g-qa-new/personal/zhangjie/tss/afag/agag')
##    obj.cleanSftpDir('/g-qa-new/personal/zhangjie/tss')
##    a = obj.listSftpDir('/g-qa-new/personal/zhangjie')
##    for x in a.keys():
##        print x, a[x]
##    obj.close()

    
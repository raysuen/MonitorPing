#!/usr/bin/env python
# _*_coding:utf-8_*_
# Auth by raysuen
#v01

import time,os,signal
import datetime
import sys,re
import smtplib
from email.header import Header
from email.mime.text import MIMEText
import subprocess

losspos=[]
lossdict={
    "lossrate":None,
    "samplenum":100,
    "alarmtime":None,
    "alarmtimeinterval":None
          }

emaildict={
    "from":"opsmonitor@hrtpayment.com",
    "to":"opsmonitor@hrtpayment.com",
    "subject":"ping丢包率达到",
    "user":"opsmonitor",
    "userpwd":"Hrt62353131.",
    "mailserver":"10.51.88.91"
            }

pingdict={
    "filename":None,
    "fileno":None,
    "destinationip":None,
    "mvtime":None
        }

def SendEmail():
    message = MIMEText("ping丢包率报警", 'plain', 'utf-8')
    message['From'] = emaildict["from"]  # 邮件上显示的发件人
    message['To'] = emaildict["to"]  # 邮件上显示的收件人
    message['Subject'] = Header(emaildict["subject"] + "<" + str(lossdict["lossrate"]) + "%>", 'utf-8')  # 邮件主题
    # message['Subject'] = Header(emaildict["subject"] + "<" + "" + "%>", 'utf-8')
    try:
        smtp = smtplib.SMTP()  # 创建一个连接
        smtp.connect(emaildict["mailserver"])  # 连接发送邮件的服务器
        smtp.login(emaildict["user"], emaildict["userpwd"])  # 登录服务器
        smtp.sendmail(emaildict["from"], emaildict["to"].split(","), message.as_string())  # 填入邮件的相关信息并发送
        print("邮件发送成功！！！")
        # smtp.quit()
        smtp.close()
        return True
    except Exception as e:
        print(e)
        print("邮件发送失败！！！")
        return False

def LossAlarm():
    if (lossdict["alarmtime"] == None or (lossdict["alarmtime"]+lossdict["alarmtimeinterval"]*60) < round(time.time())):   #判断上一次报警时间是否为None(没有报警)，或当前时间小于下一次报警时间。则不报警发邮件
        SendEmail()           #发送报警邮件
        lossdict["alarmtime"] = round(time.time())    #更新当前报警时间
    else:
        print("上次报警时间：%s"%time.strftime("%Y%m%d %H:%M:%S",time.localtime(lossdict["alarmtime"])))
        print("下次报警时间：%s" %time.strftime("%Y%m%d %H:%M:%S",time.localtime(lossdict["alarmtime"]+lossdict["alarmtimeinterval"]*60)))
        print("未达到报警时间间隔，不发送邮件")

#判读丢包率的函数
def JudgeLossRate(line):
    if line.find("time out") >= 0:       #判读当前行是否为丢包行
        if lossdict["lossrate"] == 1:    #如果丢包率为1的时候则直接报警
            LossAlarm()                  #执行报警函数
            losspos.clear()              #清空报警数组内容
        else:                            #丢包率非1时
            if len(losspos) < lossdict["lossrate"]-1:      #判读list数组内的丢包次数是否小于丢包率的次数
                losspos.append(int(line.split("=")[1].strip("\n")))           #把丢包的icmp_seq值存入list数组
            else:                                           #数组内的丢包行数大于等于丢包率-1
                if int(line.split("=")[1].strip("\n")) - losspos[0] <= lossdict["samplenum"]:   #当前行的icmp_seq号-list数组内第一个元素的icmp_seq是否小于采样数，小于等于则报警，否则把list数组内的第一个元素删除，在尾部添加当前丢包行的icmp_seq号
                    LossAlarm()      #执行报警函数
                    losspos.clear()   #清空list数组所有元素
                else:
                    losspos.pop(0)         #弹出list数组第一个元素
                    losspos.append(int(line.split("=")[1].strip("\n")))    #在list数组尾部追加当前行的icmp_seq


def ReadFile(readpos):
    ret = 0       #返回值
    with open(r"%s"%pingdict["filename"]) as f:      #读取文件
        if readpos==0:                   #判读传入的光标位置，为0则从头开始读取
            for line in f:
                JudgeLossRate(line)      #把当前行信息传入，判读丢包率的函数
            ret = f.tell()               #文件读取结束，返回光标位置
        else:
            f.seek(readpos,0)            #光标位置不为0，则从光标位置开始读取
            for line in f:
                JudgeLossRate(line)
            ret = f.tell()
    return ret

#判断邮件地址格式
def verifyEmail(email):
    ret = False
    pattern = r'^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$'
    if re.match(pattern,email) is not None:
        ret = True
    return ret


def help_func():
    print("""
    NAME:
        MonitorPing  --Monitor network loss package rate.
    SYNOPSIS:
        MonitorPing [-f] [file name] [-i] [interval time] [-r] [alarm loss rate] [-e] [email reciever] [-d] [destination IP]
    DESCRIPTION:
        -f  specify file names.
        -i  specify a alarm interval time,It must be number.Units:minut.
        -r  specify a missing percentage,It must be number,It can not less then 0.1.
        -e  specify a email reciever.
        -d  specify a IP for ping.
    EXAMPLE:
        MonitorPing -f /tmp/ping/ping.txt -i 2 -r 10 -e opsmonitor@xxx.com -d 192.168.1.1
    """)


#判断传入变量为一个正数
def is_number(num):
    pattern = re.compile(r'^[-0-9]\d*\.\d*$|\.?[0-9]\d*$')
    result = pattern.match(num)
    if result:
        return True
    else:
        return False

#判断IP格式
def check_ip(ipAddr):
  compile_ip=re.compile('^(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|[1-9])\.(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)\.(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)\.(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)$')
  if compile_ip.match(ipAddr):
    return True
  else:
    return False

def GetParameters():
    num = 1
    exitnum = 0
    # 获取参数
    if len(sys.argv) > 1:  # 判断是否有参数输入
        while num < len(sys.argv):
            if sys.argv[num] == "-h":
                help_func()  # 执行帮助函数
                exitnum = 0
                exit(exitnum)
            elif sys.argv[num] == "-f":  #指定ping结果的文件名
                num += 1  # 下标向右移动一位
                if num >= len(sys.argv):  # 判断是否存在当前下标的参数
                    exitnum = 99
                    print("The parameter must be specified a value,-f.")
                    exit(exitnum)
                elif re.match("^-", sys.argv[num]) == None:  # 判断当前参数是否为-开头，None为非-开头
                    pingdict["filename"] = sys.argv[num]
                    num += 1
                else:
                    print("Please specify a valid value for -f.")
                    exitnum = 98
                    exit(exitnum)
            elif sys.argv[num] == "-r":     #指定丢包率
                num += 1
                if num >= len(sys.argv):             #判断参数后面是否还有可提供的参数
                    exitnum = 97
                    print("The parameter must be specified a value,-r.")
                    exit(exitnum)
                elif re.match("^-", sys.argv[num]) == None:            #判断当前参数是否为-开头
                    if sys.argv[num].isdigit() == True:  # 判断是否为正整数
                        lossdict["lossrate"] = int(sys.argv[num])
                        num += 1
                    elif is_number(sys.argv[num]) == True:  #判断为正数
                        if float(sys.argv[num]) < 0.1:      #不能小于0.1
                            print("The value of -r must be great 0.1 .")
                            exitnum = 96
                            exit(exitnum)
                        else:
                            lossdict["lossrate"] = round(float(sys.argv[num])*10)     #如果为浮点数，则把采样率调整为正整数，
                            lossdict["samplenum"] = 1000                              #采样数量为1000
                            num += 1
                    else:
                        print("The value of -r must be number.")
                        exitnum = 95
                        exit(exitnum)
                else:
                    print("Please specify a valid value for -r.")
                    exitnum = 94
                    exit(exitnum)
            elif sys.argv[num] == "-i":  #指定报警时间间隔,默认为分钟
                num += 1  # 下标向右移动一位
                if num >= len(sys.argv):  # 判断是否存在当前下标的参数
                    exitnum = 93
                    print("The parameter must be specified a value,-i.")
                    exit(exitnum)
                elif re.match("^-", sys.argv[num]) == None:  # 判断当前参数是否为-开头，None为非-开头
                    if sys.argv[num].isdigit() == True:
                        lossdict["alarmtimeinterval"] = int(sys.argv[num])
                        num += 1
                    else:
                        print("The value of -i must be digit.")
                        exitnum = 92
                        exit(exitnum)
                else:
                    print("Please specify a valid value for -i.")
                    exitnum = 91
                    exit(exitnum)
            elif sys.argv[num] == "-e":  #指定报警邮件收件人，可以多人，以逗号分隔
                num += 1  # 下标向右移动一位
                if num >= len(sys.argv):  # 判断是否存在当前下标的参数
                    exitnum = 90
                    print("The parameter must be specified a value,-e.")
                    exit(exitnum)
                elif re.match("^-", sys.argv[num]) == None:  # 判断当前参数是否为-开头，None为非-开头
                    if verifyEmail(sys.argv[num]) == True:
                        emaildict["to"] = sys.argv[num]
                        num += 1
                    else:
                        print("Please specify a valid value for -e.")
                        exitnum = 89
                        exit(exitnum)
                else:
                    print("Please specify a valid value for -e.")
                    exitnum = 88
                    exit(exitnum)

            elif sys.argv[num] == "-d":  #指定ping命令的IP
                num += 1  # 下标向右移动一位
                if num >= len(sys.argv):  # 判断是否存在当前下标的参数
                    exitnum = 90
                    print("The parameter must be specified a value,-d.")
                    exit(exitnum)
                elif re.match("^-", sys.argv[num]) == None:  # 判断当前参数是否为-开头，None为非-开头
                    if check_ip(sys.argv[num]) == True:
                        pingdict["destinationip"] = sys.argv[num]
                        num += 1
                    else:
                        print("Please specify a valid value for -d.")
                        exitnum = 89
                        exit(exitnum)
                else:
                    print("Please specify a valid value for -d.")
                    exitnum = 88
                    exit(exitnum)


def KillSubprocessPing(pingpid):
    # os.killpg(os.getpgid(pingpid), signal.SIGKILL)
    pidlist = subprocess.getstatusoutput("""ps -ef | grep "ping %s" | grep -v grep | awk '{print $2}'"""%pingdict["destinationip"])
    for i in pidlist[1].split("\n"):
        os.kill(int(i),signal.SIGKILL)

def MoveFile():
    ret = False
    if round(time.time()) - pingdict["mvtime"] > 3600:
    # if round(time.time()) - pingdict["mvtime"] > 600:
        filenum = 0
        while True:
            targetfile = "%s.%s_%d" % (pingdict["filename"], time.strftime("%Y%m%d%H", time.localtime()), filenum)
            if os.path.isfile("%s" % targetfile):
                filenum += 1
            else:
                os.rename(pingdict["filename"], targetfile)
                pingdict["mvtime"] = round(time.time())
                ret = True
                break

    return ret


def ExecPing():
    if os.path.isfile("%s"%pingdict["filename"]):
        filenum=0
        while True:
            targetfile="%s.%s_%d"%(pingdict["filename"],time.strftime("%Y%m%d%H",time.localtime()),filenum)
            if os.path.isfile("%s"%targetfile):
                filenum+=1
            else:
                os.rename(pingdict["filename"],targetfile)
                break
    losspos.clear()  # 清空list数组所有元素
    pingdict["fileno"] = open("%s" % pingdict["filename"], "a")
    pop = subprocess.Popen("""ping %s | awk -F'[ =]+' -v icmpseq=0 '{if(icmpseq==0){icmpseq++}else if(icmpseq==$6){print $0"\t" strftime("%%H:%%M:%%S",systime()) ;icmpseq++;fflush()}else if(icmpseq!=$6){for(i=0;i<$6-icmpseq;i++){print "time out\ticmp_seq="icmpseq+i}print $0"\t" strftime("%%H:%%M:%%S",systime());icmpseq=$6+1;fflush()}else {print $0"\t" strftime("%%H:%%M:%%S",systime());fflush()}}'"""%(pingdict["destinationip"]),shell=True,stdout=pingdict["fileno"])
    return pop.pid

if __name__ == "__main__":
    # SendEmail()

    GetParameters()   #获取参数
    #判断是否正确传入参数,不能为None，必须要被赋值
    if pingdict["filename"] == None:
        print("You must specify a file path.")
        exit(39)
    if lossdict["lossrate"] == None:
        print("You must specify a value for ping loss rate.")
        exit(38)
    if lossdict["alarmtimeinterval"] == None:
        print("You must specify a value for alarm interval time.")
        exit(37)
    if pingdict["destinationip"] == None:
        print("You must specify a value for IP address.")
        exit(36)

    #执行Ping命令
    pingpid = ExecPing()

    #记录当前的时间戳
    if pingdict["mvtime"] == None:
        pingdict["mvtime"] = round(time.time())
    #开始读取ping命令的结果存放文件
    fpos=ReadFile(0)    #读取文件函数，返回当前文件的光标位置，第一次读取传入光标位置0
    time.sleep(20)
    #循环读取文件
    while True:
        fpos = ReadFile(fpos)          #读取文件函数，返回当前文件的光标位置
        time.sleep(20)
        if MoveFile():                 #每小时给ping结果文件重命名
            KillSubprocessPing(pingpid)      #如果重命名，则杀掉ping命令进程及其的所有的子进程
            pingpid = ExecPing()             #重新执行ping命令
            fpos=0

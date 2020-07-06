import socket
import threading
import random

class Server:
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    connections = []

    def __init__(self, port):
        self.sock.bind(('', port))
        self.sThread = threading.Thread(target=self.run)
        self.sThread.daemon = True
        self.sThread.start()
        self.msg = ""

    def handler(self, c, a):
        c.send(bytes('Connected', 'utf-8'))

    def run(self):
        while True:
            recvData, clientInfo = self.sock.recvfrom(1024)
            print(recvData.decode())
            msg = self.msg
            print(msg)
            self.sock.sendto(msg,clientInfo)
            # c, a = self.sock.accept()
            # self.cThread = threading.Thread(target=self.handler, args=(c,a))
            # self.cThread.daemon = True
            # self.cThread.start()
            # self.connections.append(c)
            # print(str(a[0]) + ':' + str(a[1]) + ' connected.')

    def announce(self, msg, host):
        self.msg = msg
        # for connection in self.connections:
        #     connection.sendto(bytes(msg, 'utf-8'), host)



# from socket import *
# import threading,os,time
 
# class Server():
#     def __init__(self,host='127.0.0.1',port=9990):
#         try: 
#             addr=(host,port)
#             self.tcpSerSock=socket(AF_INET,SOCK_STREAM)
#             self.tcpSerSock.setsockopt(SOL_SOCKET,SO_REUSEADDR,1)
#             self.tcpSerSock.bind(addr)
#             self.tcpSerSock.listen(5)
#         except Exception as e :
#             print( 'ip or port error :',str(e) )
#             self.tcpSerSock.close()
            
#     def main(self):
#         while 1 :
#             try :
#                 print( 'wait for connecting ...' )
#                 tcpCliSock,addr = self.tcpSerSock.accept()
#                 addrStr = addr[0]+':'+str(addr[1])
#                 print( 'connect from',addrStr )
#             except KeyboardInterrupt:
#                 self.close=True
#                 tcpCliSock.close()
#                 self.tcpSerSock.close()
#                 print( 'KeyboardInterrupt' )
#                 break
#             ct = ClientThread(tcpCliSock,addrStr) 
#             ct.start()
            
# class ClientThread(threading.Thread):
#     def __init__(self,tcpClient,addr):
#         super(ClientThread,self).__init__()
        
#         self.tcpClient = tcpClient
#         self.addr = addr
#         self.timeout = 60
#         tcpClient.settimeout(self.timeout)
#         self.cf = tcpClient.makefile('rw',0)
        
#     def run(self):
#         while 1:
#             try:
#                 data = self.cf.readline().strip()
#                 if data:
#                     if data.find("set time")>=0:
#                         self.timeout = int(data.replace("set time ",""))
#                         self.tcpClient.settimeout(self.timeout)
#                     print(self.addr,"client say:",data)
#                     self.cf.write(str(self.addr)+" recevied ok!"+"\n")
#                 else:
#                     break
#             except Exception as e:
#                 self.tcpClient.close()
#                 self.cf.write("time out !"+"\n")
#                 print(self.addr,"send message error,",str(e))
 
 
# if __name__ == "__main__" :
#     ser = Server()
#     ser.main()
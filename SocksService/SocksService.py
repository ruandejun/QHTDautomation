#!/usr/bin/python3.7
# -*- coding:utf8 -*-
# vim: set fileencoding=utf8
'''
SocksService is a Service of Socks
'''

import socketserver
import struct
import socket
import select
import paramiko
import logging
logging.basicConfig(level=logging.DEBUG)
SOCKS_VERSION = 5

from socketserver import ThreadingMixIn, TCPServer, StreamRequestHandler

class ThreadingTCPServer(ThreadingMixIn, TCPServer):
    pass


class SocksException(Exception):
    '''
        Base Socks Exception
    '''
    pass


class SocksIdentifyException(SocksException):
    """
        Socks identify protocol deal fail
    """
    pass


class SocksIdentifyFailed(SocksIdentifyException):
    """
        Socks identify fail
    """
    pass


class SocksIdentifyDisabled(SocksIdentifyException):
    """
        No identify require
    """
    pass


class SocksNegotiateException(SocksException):
    """
        Negotiate Exception
    """
    pass


class SocksAddressTypeDisabled(SocksNegotiateException):
    """
        Address flag not support
    """
    pass


class SocksRemoteException(SocksException):
    """
        remote socks error
    """
    pass


class SocksClientException(SocksException):
    """
        client error
    """
    pass


class SocksProxy(StreamRequestHandler):
    username = 'username'
    password = 'password'

    def handle(self):
        logging.info('Accepting connection from %s:%s' % self.client_address)

        # greeting header
        # read and unpack 2 bytes from a client
        header = self.connection.recv(2)
        version, nmethods = struct.unpack("!BB", header)

        # socks 5
        assert version == SOCKS_VERSION
        assert nmethods > 0

        # get available methods
        methods = self.get_available_methods(nmethods)

        # accept only USERNAME/PASSWORD auth
        if 2 not in set(methods):
            # close connection
            self.server.close_request(self.request)
            return

        # send welcome message
        self.connection.sendall(struct.pack("!BB", SOCKS_VERSION, 2))

        if not self.verify_credentials():
            return

        # request
        version, cmd, _, address_type = struct.unpack("!BBBB", self.connection.recv(4))
        assert version == SOCKS_VERSION

        if address_type == 1:  # IPv4
            address = socket.inet_ntoa(self.connection.recv(4))
        elif address_type == 3:  # Domain name
            domain_length = self.connection.recv(1)[0]
            address = self.connection.recv(domain_length)
            address = socket.gethostbyname(address)
        port = struct.unpack('!H', self.connection.recv(2))[0]

        # reply
        try:
            if cmd == 1:  # CONNECT
                remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote.connect((address, port))
                bind_address = remote.getsockname()
                logging.info('Connected to %s %s' % (address, port))
            else:
                self.server.close_request(self.request)

            addr = struct.unpack("!I", socket.inet_aton(bind_address[0]))[0]
            port = bind_address[1]
            reply = struct.pack("!BBBBIH", SOCKS_VERSION, 0, 0, 1,
                                addr, port)

        except Exception as err:
            logging.error(err)
            # return connection refused error
            reply = self.generate_failed_reply(address_type, 5)

        self.connection.sendall(reply)

        # establish data exchange
        if reply[1] == 0 and cmd == 1:
            self.exchange_loop(self.connection, remote)

        self.server.close_request(self.request)

    def get_available_methods(self, n):
        methods = []
        for i in range(n):
            methods.append(ord(self.connection.recv(1)))
        return methods

    def verify_credentials(self):
        version = ord(self.connection.recv(1))
        assert version == 1

        username_len = ord(self.connection.recv(1))
        username = self.connection.recv(username_len).decode('utf-8')

        password_len = ord(self.connection.recv(1))
        password = self.connection.recv(password_len).decode('utf-8')

        if username == self.username and password == self.password:
            # success, status = 0
            response = struct.pack("!BB", version, 0)
            self.connection.sendall(response)
            return True

        # failure, status != 0
        response = struct.pack("!BB", version, 0xFF)
        self.connection.sendall(response)
        self.server.close_request(self.request)
        return False

    def generate_failed_reply(self, address_type, error_number):
        return struct.pack("!BBBBIH", SOCKS_VERSION, error_number, 0, address_type, 0, 0)

    def exchange_loop(self, client, remote):

        while True:

            # wait until client or remote is available for read
            r, w, e = select.select([client, remote], [], [])

            if client in r:
                data = client.recv(4096)
                if remote.send(data) <= 0:
                    break

            if remote in r:
                data = remote.recv(4096)
                if client.send(data) <= 0:
                    break

class SocksRequestHandler(socketserver.StreamRequestHandler):
    """
        defined get_sockes5_* functions to get remote socket for
        socksv5.
        defined socksv5_identifier to deal socksv5 identifier
        handle to select socks v5 or socks v4, only socksv5
        support now.
        defined handle_socks5 to deal sockesv5 required
    """
    def log(self, level, msg):
        """
        function to log info
        """
        pass  # print level,msg

    def get_s5_conn_sp(self, dst, src, dst_type='\x01'):
        '''
            create remote connect and return socket of this connect
            dst is a tuple (addr,port) which is connect dst
            dst_type x01 is ipv4
                     x02 is host_name
                     x04 is ipv6
            return remote_socket
        '''
        if (hasattr(self, 'server') and
                hasattr(self.server, 'socks') and
                hasattr(self.server.socks, 'connect_handle') and
                callable(self.server.socks.connect_handle)):
            return self.server.socks.connect_handle(dst,
                                                    src,
                                                    dst_type)
        return None, None

    def get_s5_bind_sp(self, dst, src, dst_type='\x01'):
        """
            create remote bind socket like get_socksv5_connect_socket
        """
        _, port = dst
        if dst_type in ['\x01', '\x03']:
            remote = socket.socket(socket.AF_INET,
                                   socket.SOCK_STREAM)
            remote.settimeout(5)
            remote.bind(('127.0.0.1', port + 9000))
            remote.listen(0)
        elif dst_type == '\x04':
            remote = socket.socket(socket.AF_INET6,
                                   socket.SOCK_STREAM)
            remote.bind(('::', port + 9000))
            remote.listen(0)
        return remote

    def get_socks5_udp_socket(self, dst, src, dst_type='\x01'):
        """
            create remote udp socket
        """
        pass

    def socks5_identifier(self, methods):
        """
            socks v5 identificate active
            switch a identify method and finish methods
            if identify fail will raise Exception
        """
        if b'\x00' in methods:
            self.request.send(b'\x05\x00')
            return True
        else:
            msg = 'Just support No authentication required'
            raise SocksIdentifyDisabled(msg)

    def handle(self):
        """
            required entry to judge protocol version,
            select deal method and call it
        """
        recv = self.request.recv(512)
        print('debug', 'recv msg:%r' % recv, recv[0])
        self.log('debug', 'recv msg:%r' % recv)
        if recv[1] == 4:
            self.handle_socks4(recv)
        elif recv[0] == 5:
            self.handle_socks5(recv)

    def handle_socks4(self, recv):
        pass

    def handle_socks5(self, recv):
        def exchange_data(remote_peer, local_peer, debug=None):
            """
                exchange ssh channel socket with socks socket
            """
            while True:
                r, _, e = select.select([remote_peer, local_peer],
                                        [], [])
                if remote_peer in r:
                    try:
                        recv = remote_peer.recv(4096)
                    except (socket.error, socket.timeout) as e:
                        raise SocksRemoteException(e)
                    try:
                        if local_peer.send(recv) <= 0:
                            break  # 向本地发送远端回复
                    except (socket.error, socket.timeout) as e:
                        raise SocksClientException(e)
                if local_peer in r:
                    try:
                        recv = local_peer.recv(4096)
                    except (socket.error, socket.timeout) as e:
                        raise SocksClientException(e)
                    try:
                        if remote_peer.send(recv) <= 0:
                            break  # 向远端发送请求
                    except (socket.error, socket.timeout) as e:
                        raise SocksRemoteException(e)

        def reply_client_bnd(atype, addr, port):
            """
                return success BND protocol return sequences
            """
            self.log('debug', 'atype:%r ,(%s,%d)' % (atype,
                                                     addr,
                                                     port))
            if atype == b'\x01':  # ipv4

                msg = b'\x05\x00\x00\x01%s%s' % (
                    socket.inet_aton(addr),
                    struct.pack(">H", port))
            elif atype == b'\x03':  # domain

                msg = b'\x05\x00\x00\x03%s%s%s' % (
                    struct.pack('>H', len(addr)),
                    addr,
                    struct.pack(">H", port))
            elif atype == b'\x04':  # ipv6

                msg = b'\x05\x00\x00\x04%s%s' % (
                    socket.inet_pton(socket.AF_INET6, addr),
                    struct.pack(">H", port))
            else:
                raise SocksAddressTypeDisabled
            self.log('debug', 'send to client:%r' % msg)
            self.request.send(msg)


        nmethod, = struct.unpack('b', recv[1:2])
        methods = recv[2:2 + nmethod]
        self.socks5_identifier(methods)
        try:
            version, cmd, _, atype = self.request.recv(4)
        except ValueError as e:
            self.log('error', 'client send error request')
            self.log('debug', '%r' % e)
            raise e
        self.log('debug', 'recv msg:%r%r%r%r' % (version,
                                                 cmd,
                                                 _,
                                                 atype))
        try:

            if atype == 1:  # ipv4
                addr = socket.inet_ntoa(self.request.recv(4))
            elif atype == 3:  # domain
                addr = self.request.recv(
                    ord(self.request.recv(1).decode('utf-8')[0]))
            elif atype == 4:  # ipv6
                addr = socket.inet_ntop(socket.AF_INET6,
                                        self.request.recv(16))
            else:
                raise SocksAddressTypeDisabled
            port = struct.unpack('>H', self.request.recv(2))[0]
            self.log('notify', 'client request:(%s,%d)' % (addr, port))

            if cmd == 1:  # connect
                remote_sp, remote_atype = \
                    self.get_s5_conn_sp((addr, port), \
                                        self.request.getpeername(), \
                                        atype)
                # don't get remote socket
                if remote_sp is None: return
                try:
                    bnd_addr, bnd_port = remote_sp.getpeername()
                except socket.error as e:
                    raise e
                self.log('notify',
                         'connect remote bnd:(%s,%d)' % (bnd_addr,
                                                         bnd_port))

                reply_client_bnd(remote_atype, bnd_addr, bnd_port)
                exchange_data(remote_sp, self.request)
            elif cmd == 2:  # bind
                remote_sp, remote_atype = \
                    self.get_s5_bind_sp((addr, port), \
                                        self.request.getpeername(), \
                                        atype)
                if remote_sp is None: return
                try:
                    bnd_addr, bnd_port = remote_sp.gethostname()
                except socket.error as e:
                    raise e
                self.log('notify',
                         'bind remote bnd:(%s,%d)' % (bnd_addr,
                                                    bnd_port))
                reply_client_bnd(remote_atype, bnd_addr, bnd_port)
                exchange_data(remote_sp, self.request)
            elif cmd == 3:  # udp
                pass
        except SocksException as e:
            self.log('warning', 'SocksException:%s' % e)


class SocksRemoteRequestHandler(object):

    def connect_handle(self, dst, src, dst_type=b'\x01'):
        print('==SocksRemoteRequestHandler==')
        if dst_type in [1, 3]:
            remote_atype = 1
            remote = socket.socket(socket.AF_INET,
                                   socket.SOCK_STREAM)
            remote.settimeout(5)
            remote.connect(dst)
        elif dst_type == 4:
            remote_atype = 4
            remote = socket.socket(socket.AF_INET6,
                                   socket.SOCK_STREAM)
            remote.settimeout(5)
            remote.connect(dst)
        return remote, remote_atype


    def bind_handle(self, dst, src, dst_type=b'\x01'):
        return None, None

    def udp_handle(self, dst, src, dst_type=b'\x01'):
        return None, None


class SocksSSHRemoteRequestHandler(SocksRemoteRequestHandler):
    """
    create a ssh channel
    """
    old_conversation = None
    errnum = 0
    reconnectnum = 0

    def __init__(self, domain, username, password, port=22,stop=None):
        """
        init ssh info
        """
        self.domain = domain
        self.username = username
        self.password = password
        self.port = port
        self.stop = stop
    def get_conversation(self):
        '''
        create a ssh conversation
        '''
        conversation = paramiko.SSHClient()
        ssh_policy = paramiko.WarningPolicy()
        conversation.set_missing_host_key_policy(ssh_policy)
        try:
            print('==get_conversation==')
            conversation.connect(self.domain,
                                 port=self.port,
                                 timeout=5,
                                 username=self.username,
                                 password=self.password)

        except Exception as e:
            print ("con't connect ssh server:", e)
            raise SocksRemoteException("con't connect ssh server:", e)
        return conversation

    def get_socket(self, conversation, dst, src):
        print('==get_socket==')
        try:
            trans = conversation.get_transport()
            res = trans.open_channel('direct-tcpip', dst, src)
            res.settimeout(5)
            return res
        except paramiko.ChannelException as e:
            print ('retry %s:%d' % dst)
            try:
                trans = conversation.get_transport()
                res = trans.open_channel('direct-tcpip', dst, src)
                res.settimeout(5)
                return res
            except paramiko.ChannelException as e:
                self.errnum += 1
                #self.stop.put('stop')
                raise SocksRemoteException(e)

    def connect_handle(self, dst, src, dst_type=b'\x01'):
        print('==connect_handle==')
        if self.old_conversation is None:
            self.old_conversation = self.get_conversation()
        try:
            sp = self.get_socket(self.old_conversation, dst, src)
            self.reconnectnum = 0
        except paramiko.SSHException:
            if not self.reconnectnum > 5:
                self.reconnectnum += 1
                self.old_conversation = self.get_conversation()
                return self.connect_handle(dst, src, dst_type)
            else:
                raise SocksRemoteException('多次重试无效')
        return sp, b'\x01'


class SocksServer(socketserver.TCPServer):
    def __init__(self,
                 server_address,
                 RequestHandlerClass,
                 TunnelHandler,
                 bind_and_activate=True):
        if isinstance(TunnelHandler, SocksRemoteRequestHandler):
            print('==sock==')
            self.socks = TunnelHandler
        else:
            raise SocksRemoteException
        try:
            print('====TCPServer====')
            socketserver.TCPServer.__init__(self, server_address,
                                            RequestHandlerClass,
                                            bind_and_activate)
        except socket.error as e:
            if e.errno == 98:
                print('Address already in use, Socks service start failed')
            else:
                print(e)
            #exit()


class ThreadingSocksServer(socketserver.ThreadingMixIn, SocksServer):
    daemon_threads = True
    # much faster rebinding
    allow_reuse_address = True

    # def __init__(self, server_address, SocksServer):
    #     socketserver.TCPServer.__init__(self, server_address, SocksServer)


class ForkingSocksServer(socketserver.ThreadingMixIn, SocksServer):
    pass

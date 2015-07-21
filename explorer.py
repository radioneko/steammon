#! /usr/bin/env python2
import BaseHTTPServer
import SocketServer
import json

class http_sniffer(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(s):
        s.send_response(200)
        s.send_header('Content-Type', 'text/plain')
        s.end_headers()
        s.wfile.write('Cookies captured\n')
        hdr = dict()
        for k, v in s.headers.items():
            print('%s => %s' % (k, v))
            if k not in ('host', 'accept-encoding', 'cache-control', 'pragma'):
                hdr[k] = v
        with open('.steamrc', 'w') as f:
            f.write(json.dumps(hdr, indent=2))

PORT = 80

Handler = http_sniffer

SocketServer.TCPServer.allow_reuse_address = True
httpd = SocketServer.TCPServer(("", PORT), Handler)

print "serving at port", PORT
httpd.serve_forever()

# -*- coding: utf-8 -*-
from __future__ import print_function
import cgi
import time
import BaseHTTPServer as httpserver

from functools import partial, reduce
import operator as op

from collections import OrderedDict
#import ghostscript #really buggy didn't get it to work properly.. NOTE you have to have ghostscript installed
from subprocess import call
from tempfile import NamedTemporaryFile

HOSTNAME, PORT = '192.168.1.85', 80

def unpack(f, a):
    return f(*a)
def unpackd(f,a):
    return f(**a)
def tee(a):
    print(a)
    return a

class Handler(httpserver.BaseHTTPRequestHandler):
    def do_GET(self):
        print("GET")
        self.send_response(200)
        self.send_header('Content-type','text/plain')
        self.end_headers()
        self.wfile.write('GET')

    def do_POST(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                'REQUEST_METHOD':'POST', 
                'CONTENT_TYPE':self.headers['Content-Type'],
            }
        )
        
        pdf_properties = dict(
            delete=False, 
            suffix='.pdf'
        )
        output_pdf_properties = dict(
            pdf_properties,
            **dict(
                mode='r',
            )
        )

        try:
            def prepare_pdf_file(field_item):
                file_data = field_item.file.read()
                temp_file = NamedTemporaryFile(**pdf_properties)
                temp_file.write(file_data)
                temp_file.flush()
                print('Uploaded "{filename}" ({size} bytes)'.format( filename=field_item.filename, size=len(file_data)))
                return temp_file
            
            def is_file(field_item):
                return bool(field_item.filename)

            sorted_input = OrderedDict(
                sorted(
                    dict(form).iteritems()
                )
            ) #NOTE form has them unsorted, could perhaps be inorder if all input fields have the same name (gets a list instead) #NOTE this is ugly since type(form) is ugly
            
            temp_input = map(
                prepare_pdf_file,
                filter(
                    is_file,
                    sorted_input.values()
                )
            )
            if(temp_input<1):
                self.send_response(404)
                self.end_headers()        
            
            #gs -dBATCH -dNOPAUSE -q -sDEVICE=pdfwrite -sOutputFile=finished.pdf file1.pdf file2.pdf
            temp_output = NamedTemporaryFile(**output_pdf_properties)
            command = [
                "gs",
                "-dBATCH", 
                "-dNOPAUSE", 
                "-q",
                "-sDEVICE=pdfwrite", 
                "-sOutputFile={filename}".format(
                    filename=temp_output.name
                )
            ]+\
            map(
                op.attrgetter('name'), 
                temp_input
            )
            print(' '.join(command)) 
            call(command) #pretty safe since all inputs to the command string is temp filenames (no ``filename injection'' possible) #NOTE waits until returning
        
            self.send_response(200)
            self.send_header("Content-type", "application/pdf")
            self.end_headers()
            
            self.wfile.write(temp_output.read())
 
        except TypeError as e:
            print("Error:", e)
            self.send_response(500)
            self.end_headers()
        finally: #NOTE all the try-except's inside finally is to guard of not set variables
            try:
                temp_output.close()
            except:
                pass
            try: 
                for f in pdf_files: #temporary files are deleted after they are closed so beware, cannot use ``with'' in this case
                    try:
                        f.close()
                    except:
                        pass
            except:
                pass

if __name__ == "__main__":
    httpd = httpserver.HTTPServer((HOSTNAME, PORT), Handler)
    print(time.asctime(), "Server start - {name}:{port}".format(name=HOSTNAME, port=PORT))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print(time.asctime(), "Server stops - {name}:{port}".format(name=HOSTNAME, port=PORT))


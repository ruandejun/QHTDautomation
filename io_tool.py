#!/usr/bin/python
# -*- coding: utf-8 -*-   
#
#  io_tool.py
#  Xcode-IPython
#
#  Created by V.Anh Tran on 08/09/2012.
#  Copyright (c) 2012 __MyCompanyName__. All rights reserved.
#

import sys,os,base64,json

class Config:
	"""
	Save , load config from file
	"""
	def __init__(self,appFolderPath,fileName='config.txt'):
		self.appFolderPath=appFolderPath;
		self.fileName=fileName;
	
	def encode(self,dataObject):
		return base64.b64encode(json.dumps(dataObject));
	
	def decode(self,encodedData):
		try:
			return json.loads(base64.b64decode(encodedData));
		except:
			pass; # to fallback decode
		
		try:
			return eval(encodedData);
		except Exception as e:
			return {};
		
	def load(self):
		try:
			f=open(self.appFolderPath+'/'+self.fileName,'r');
			data=self.decode(f.read());
			f.close();
		except IOError as e:
			if e[0]==2: #No such file or directory
				return {};
			else:
				raise e;
		else:
			return data;
			
	def save(self,data):
		textData=self.encode(data);
		while 1:	
			try:
				f=open(self.appFolderPath+'/'+self.fileName,'w');
				f.write(textData);
				f.close();
			except Exception as e:
				print (e);
				pass;
			else:
				try:
					f2=open(self.appFolderPath+'/'+self.fileName,'r');
					test=f2.read();
					f2.close();
				except Exception as e:
					continue;
				
				if len(test)>1:
					if len(test)==len(textData):
						return True;
					else:
						return False;
	
	def get(self,key,default=None):
		data=self.load();
		return data.get(key,default);
	
	def set(self,key,value):
		data=self.load();
		data[key]=value;
		return self.save(data);
		

def copyToClipboard(text):
	command = 'echo "%s"| pbcopy' % text;
	os.system(command);

def main():
    pass

if __name__ == "__main__": 
    sys.exit(main())

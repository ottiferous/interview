import multiprocessing  # for better pinging
import subprocess
import mmap             # for large file parsing
import os               # for ping
import re               # regex

# for sending emails
import smtplib
from email.mime.text import MIMEText

#webdav
import httplib


# class is an array of dictionary objects and methods to handle data
class DirectoryList:
   
   def __init__(self):
      self.directory = []
   
   def directory(self):
      return self.directory
   
   # search for a match and then update, otherwise make new entry
   def update(self, ip, username, time):
      if [element for element in self.directory if element['ip'] == ip]:
         element['username'] = username
         element['time'] =  time
      else:
         self.add(ip, username, time)
   
   # make a new dictionary entry in the list
   def add(self, ip, username, time):
      self.directory.append({'ip': ip, 'username': username, 'time': time})
   
   # get ips from list
   def get_ips(self):
      ip_list = []
      for entry in self.directory:
         ip_list.append(entry['ip'])
      return ip_list
   
   # get usernames
   def get_usernames(self):
      name_list = []
      for entry in self.directory:
         name_list.append(entry['username'])
      return name_list


# pings what we pass to it later
def ping(jobqueue, resultsqueue):
   DEVNULL = open(os.devnull, 'w')
   while True:
      ip = jobqueue.get()
      if ip is None: break
      try:
         subprocess.check_call(['ping', '-c 1', ip], stdout = DEVNULL)
         resultsqueue.put(ip)
      except:
         pass        # on error assume computer is not in use - no one can currently be using it


# search the lowest octet for responses using a queue
def get_ips_from_network(subnet, machines = [], pool_size = 255):
   
   jobs = multiprocessing.Queue()
   results = multiprocessing.Queue()
   pool =  [ multiprocessing.Process(target = ping, args = (jobs, results))
             for i in range(pool_size) ]
   for p in pool:
      p.start()
   # we can nest this loop further to allow pinging outside of /24
   for i in range(1, 255):
      jobs.put(subnet + str(i))
   for p in pool:
      jobs.put(None)
   for p in pool:
      p.join()
   while not results.empty():
      machines.append(results.get())
   # list of all ip addresses found
   return machines


# read lines from log file, updating the ip object if anything is found
def read_log(filename, ip_list):
   f = open(filename, 'r')
   directory = DirectoryList()
   
   # reads potentially large log file into memory before searching
   with open(filename, 'r') as f:
      mem_log = mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ)
      for line in iter(mem_log.readline, ""):
         
         #print line
         # check for an IP address match, then capture ip, name, and time via regex
         if any(ip in line for ip in ip_list):
            
            ip   = (re.search(r'(\b(?:\d{1,3}\.){3}\d{1,3}\b)', line))
            name = (re.search(r'for (\w.*) from', line ))
            time = (re.search(r'^\w+ \d{1,2} \d{2}:\d{2}:\d{2}', line))
            
            # update entry to reflect newest info we got a match for everything
            if ip and name and time:
               directory.update(ip.group(0), name.group(1), time.group(0))
   f.close()
   # return our list of up-to-date dictionaries
   return directory


# create the log file in memory
def generate_log(master_list):
   log = []
   for line in master_list.directory:
      log.append(log_format(line['ip'], line['username'], line['time']))
   
   # log file string
   return "\n".join(log)
      

# write the log file to disk
def write_to_log(filename, log):
   f = open(filename, 'w')
   f.write(log)
   f.close()


# write data in log file format
def log_format(time, username, ip):
   return "%(time)s - %(username)s is logged in on %(ip)s" % {'time': time, 'username': username, 'ip': ip}


# iterate through supplied list sending attachment to each
def send_email(name_list, attachment):
   for name in name_list:
      try:
         send(name, attachment)
      except:
         # we hit an error sending, mark that this user did not get file
         attachment += ("\nThere was an error sending the file to " + name)
   return attachment
      

# open connection and send using SMTP
def send(username, attachment):
   msg = MIMEText(attachment)
   msg['Subject'] = 'Who is online'
   msg['From'] = 'loginAdmin@apple.com'
   msg['To'] = username + '@apple.com'
   s = smtplib.SMTP('localhost')
   s.sendmail(msg['From'], [msg['To']], msg.as_string())
   s.quit()


# send file via webdav ( does not handle authentication )
def send_file_over_webdav(servername, path, log_file):
   dav_server = httplib.HTTPConnection(servername)
   dav_server.request('PUT', path, log_file)
   dav_response = dav_server.getresponse()
   dav_server.close()
   if not (200 <= dav_response.status < 300):
   	raise Exception(dav_response.status)


# iterate through available webdav list
def send_via_webdav(computer_list, log_file):
   for computer in computer_list:
      try:
         send_file_over_webdav(computer['servername'], computer['path'], log_file)
      except Exception as error:
         log_file += ("\nError sending log to " + computer['servername'] + " with HTTP error code: " + str(error.args[0]))
         return log_file


# pulls information from source (another log) of available computers to send to
def get_webdav_list():
   return [{'servername': 'testingserver.info', 'path': '/var/log/whosonline.log'}]


if __name__ == '__main__':
   
   # dummy variables for use with supplied log file
   subnet = '10.0.0.'
   log_file = "sampleLog.txt"
   output_log_loc = 'outputlog.txt'
   
   # first we get all active IP addresses on our network
   ip_list = get_ips_from_network(subnet)
   
   # make our new DirectoryList object from our known ips and handy log file
   master_list = read_log(log_file, ip_list)
   
   # create the log file for output
   log = generate_log(master_list)
   user_list = master_list.get_usernames()
   
   # email the log file out to users, updating on issues sending
   log = send_email(user_list,log)
   
   # send files through webDAV to computers in list, udpating on issues sending
   webdav_directory = get_webdav_list()
   log = send_via_webdav(webdav_directory, log)
   
   # if an error happened the log file will reflect this
   write_to_log(output_log_loc, log)
# python Exercise1.py /Users/adminuser/Documents .*.png$

import sys
import os
import re
import numpy as np
import matplotlib.pyplot as plt
from collections import OrderedDict

root_dir    = sys.argv[1]

# run some tests to make sure input is valid, directories are okay, that sort of thing
try:
   if os.path.isdir(root_dir) != True:
      sys.exit("Could not find directory" + root_dir)
   if os.access(root_dir, os.R_OK) != True:
      sys.exit("You lack permision to read from that directory")
   keyword  = re.compile(sys.argv[2])
except:
   sys.exit("OOPS! \nInvalid regular expression")

findings    = OrderedDict()

# Check for matches
for root, dirs, files in os.walk(root_dir):
   findings[root] = 0
   for fname in files:
      if keyword.match(fname):
         findings[root] += 1

# Create tuples for graphing
result      = findings.keys()
hits        = []
for key in result:
   hits.append(findings[key])

# Create plot
width       = 1
loc         = np.arange(len(result))
p1          = plt.bar(loc, hits, width, color = 'g')
xticks_pos  = [width*patch.get_width() + patch.get_xy()[0] for patch in p1]  # fixes the alignment for the 45 angle
plt.xticks(xticks_pos, result,  ha = 'right', rotation = 45)

plt.xlabel('Directory')
plt.title('Occurences of matches for: ' + sys.argv[2])

plt.show()

# output dictionary - each entry on its own line
for k in findings:
   print k, findings[k]
      
# Limitations
#      
# symlinks can cause a recursion issue ( should be disabled by default in os.walk() )
# long directory names are not guarnteed to fit on the graph
# assumes the regex is written to handle entire file names ( i.e. .png won't work but .*.png$ will )
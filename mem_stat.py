#!/usr/bin/env python3

# Print statistics from the memory subsystem in macOS.

import subprocess
import re

# Process swap stats.
# input format is:
# vm.swapusage: total = 0.00M  used = 0.00M  free = 0.00M  (encrypted)
def extractSwapStats(swapStats, label):
  numPos = swapStats.find(label) + len(label) + 3
  return int(float(swapStats[numPos:swapStats.find('M', numPos)]) * 1048576) # 1024**2

# Return a dictionary containing VM metrics.
def vmMetrics():
  metrics = {}
  separator = re.compile(':[\s]+')
  pageSize = 4096

  vmstatRaw = subprocess.Popen(['vm_stat'], stdout = subprocess.PIPE).communicate()[0].decode('utf-8')
  lines = vmstatRaw.split('\n')
  for lineIndex in range(1, len(lines) - 7):
    fields = separator.split(lines[lineIndex].strip())
    metrics[fields[0]] = int(fields[1].strip('.')) * pageSize

  sysctlList = ['sysctl',
                # This is the same as "Anonymous pages" from vm_stat. Use either one.
		# Note: "internal" means anonymous or swap backed (see note below, however), "external" means file backed.
		# Due to some VM technicalities (see FreeBSD man page for top), memory mapped file pages are counted
		# as anonymous but they are technically backed by files on disk (not swap). We can pick them out
		# because they are also "purgeable".
                #'vm.page_pageable_internal_count',
		#
		# This is the same as "File backed pages" from vm_stat.
		#'vm.page_pageable_external_count',
		#
		# This is the same as "Pages purgeable" from vm_stat.
		#'vm.page_purgeable_count',
		#
		# This is a count of dirty pages containing app data and memory mapped files.
		'vm.pageout_inactive_dirty_internal',
		#
		# This is count of dirty pages containing file data.
		'vm.pageout_inactive_dirty_external',
                #
                # Memory pressure level. This is 1 (Normal), 2 (Warn), or 3 (Critical).
                'kern.memorystatus_vm_pressure_level',
		#
		# Swap file usage stats. This should be the last entry.
		'vm.swapusage']

  sysctlRaw = subprocess.Popen(sysctlList, stdout = subprocess.PIPE).communicate()[0].decode('utf-8')
  lines = sysctlRaw.split('\n')
  # Everything except swap has a simple form.
  lineCount = len(lines)
  for lineIndex in range(0, lineCount - 2): # The last entry is an empty line.
    fields = separator.split(lines[lineIndex].strip())
    # Memory pressure level is not a page count but an integer.
    if fields[0] == 'kern.memorystatus_vm_pressure_level':
      metrics[fields[0]] = int(fields[1])
    else:
      metrics[fields[0]] = int(fields[1]) * pageSize
  # Swap.
  swapStats = lines[lineCount - 2]
  metrics['Swap total'] = extractSwapStats(swapStats, 'total')
  metrics['Swap used'] = extractSwapStats(swapStats, 'used')
  metrics['Swap free'] = extractSwapStats(swapStats, 'free')
  # Use custom vmmetrics command to retrieve free memory percentage from the OS.
  vmmRaw = subprocess.Popen(['vmmetrics'], stdout = subprocess.PIPE).communicate()[0].decode('utf-8')
  lines = vmmRaw.split('\n')
  lineCount = len(lines)
  for lineIndex in range(0, lineCount - 1): # The last entry is an empty line.
    fields = separator.split(lines[lineIndex].strip())
    metrics[fields[0]] = int(fields[1])

  return metrics

# Return a string with a nicely formatted representation of an input size in bytes.
def prettySize(size, sizeWidth, sizeDec):
  bytesToGB = 9.313225746154785e-10 # 1 / (1024**3)
  bytesToMB = 9.5367431640625e-07 # 1 / (1024**2)
  bytesToKB = 0.0009765625 # 1 / 1024

  sizeGB = size * bytesToGB
  if sizeGB >= 1.0:
    return f'{sizeGB:>{sizeWidth}.{sizeDec}f} GB'

  sizeMB = size * bytesToMB
  if sizeMB >= 1.0:
    return f'{sizeMB:>{sizeWidth}.{sizeDec}f} MB'

  sizeKB = size * bytesToKB
  if sizeKB >= 1.0:
    return f'{sizeKB:>{sizeWidth}.{sizeDec}f} KB'

  return f'{size:>{sizeWidth}} B'


# Pretty print VM metrics.

# Formatting dimensions.
labelWidth = 12
sizeWidth = 7 # Longest output is xxxx.xx
sizeDec = 2

metrics = vmMetrics()

heading = 'Breakdown of physical memory:'
print(heading)
# headDashes needs to cover the heading and the output.
# 4: ':' + ' GB' in prettySize output.
headDashes = '-' * max(len(heading), labelWidth + sizeWidth + 4)
print(headDashes)
activeLabel = 'Active'
activeBytes = metrics['Pages active']
print(f'{activeLabel:>{labelWidth}}:{prettySize(activeBytes, sizeWidth, sizeDec)}')
inactiveLabel = 'Inactive'
inactiveBytes = metrics['Pages inactive']
print(f'{inactiveLabel:>{labelWidth}}:{prettySize(inactiveBytes, sizeWidth, sizeDec)}')
freeLabel = 'Free'
freeBytes = metrics['Pages free']
print(f'{freeLabel:>{labelWidth}}:{prettySize(freeBytes, sizeWidth, sizeDec)}')
wiredLabel = 'Wired'
wiredBytes = metrics['Pages wired down']
print(f'{wiredLabel:>{labelWidth}}:{prettySize(wiredBytes, sizeWidth, sizeDec)}')
throttledLabel = 'Throttled'
throttledBytes = metrics['Pages throttled']
print(f'{throttledLabel:>{labelWidth}}:{prettySize(throttledBytes, sizeWidth, sizeDec)}')
speculativeLabel = 'Speculative'
speculativeBytes = metrics['Pages speculative']
print(f'{speculativeLabel:>{labelWidth}}:{prettySize(speculativeBytes, sizeWidth, sizeDec)}')
compressedLabel = 'Compressor'
compressedBytes = metrics['Pages occupied by compressor']
uncompressedBytes = metrics['Pages stored in compressor']
print(f'{compressedLabel:>{labelWidth}}:{prettySize(compressedBytes, sizeWidth, sizeDec)} (Uncompressed:{prettySize(uncompressedBytes, sizeWidth, sizeDec)})')
print(headDashes)
totalLabel = 'Total'
totalBytes = activeBytes + inactiveBytes + freeBytes + wiredBytes + throttledBytes + speculativeBytes + compressedBytes
print(f'{totalLabel:>{labelWidth}}:{prettySize(totalBytes, sizeWidth, sizeDec)}')

labelWidth = 5
print('')
heading = 'Swap usage:'
print(heading)
headDashes = '-' * max(len(heading), labelWidth + sizeWidth + 4)
print(headDashes)
swapUsedLabel = 'Used'
swapUsedBytes = metrics['Swap used']
print(f'{swapUsedLabel:>{labelWidth}}:{prettySize(swapUsedBytes, sizeWidth, sizeDec)}')
swapFreeLabel = 'Free'
swapFreeBytes = metrics['Swap free']
print(f'{swapFreeLabel:>{labelWidth}}:{prettySize(swapFreeBytes, sizeWidth, sizeDec)}')
print(headDashes)
swapTotalLabel = 'Total'
swapTotalBytes = metrics['Swap total']
print(f'{swapTotalLabel:>{labelWidth}}:{prettySize(swapTotalBytes, sizeWidth, sizeDec)}')

labelWidth = 25
print('')
heading = 'Additional stats:'
print(heading)
headDashes = '-' * max(len(heading), labelWidth + sizeWidth + 4)
print(headDashes)
compSaveLabel = 'Compressor is saving'
print(f'{compSaveLabel:>{labelWidth}}:{prettySize(max(uncompressedBytes - compressedBytes, 0), sizeWidth, sizeDec)}')
appMemLabel = 'Application memory usage'
appMemBytes = metrics['Anonymous pages'] - metrics['Pages purgeable']
print(f'{appMemLabel:>{labelWidth}}:{prettySize(appMemBytes, sizeWidth, sizeDec)}')
cachedFilesLabel = 'Cached files'
cachedFileByes = metrics['File-backed pages'] + metrics['Pages purgeable']
print(f'{cachedFilesLabel:>{labelWidth}}:{prettySize(cachedFileByes, sizeWidth, sizeDec)}')
topUsedLabel = 'top\'s used'
print(f'{topUsedLabel:>{labelWidth}}:{prettySize(activeBytes + inactiveBytes + wiredBytes + throttledBytes + compressedBytes, sizeWidth, sizeDec)}')
dirtyLabel = 'Dirty pages'
dirtyBytes = metrics['vm.pageout_inactive_dirty_internal'] + metrics['vm.pageout_inactive_dirty_external']
print(f'{dirtyLabel:>{labelWidth}}:{prettySize(dirtyBytes, sizeWidth, sizeDec)}')
availableLabel = 'Available memory'
availablePercent = metrics['Free memory percent']
availableBytes = int(totalBytes * availablePercent / 100)
print(f'{availableLabel:>{labelWidth}}:{prettySize(availableBytes, sizeWidth, sizeDec)}')
pressureLabel = 'Memory pressure'
pressurePercent = 100 - availablePercent
pressureLevelDict = {1 : 'Normal', 2 : 'Warn', 3 : 'Critical'}
pressureLevel = pressureLevelDict[metrics['kern.memorystatus_vm_pressure_level']]
print(f'{pressureLabel:>{labelWidth}}:{pressurePercent:>{sizeWidth}} % ({pressureLevel})')

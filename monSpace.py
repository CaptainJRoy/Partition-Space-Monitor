import netsnmp, thread, time
import curses

SESSION = 0
hrPartitionLabel = 0
prev_pct = {}

DICT = {}
REFRESH_TIME = 5
EXIT = False

def init_session():
    """
        This function initializes the session that will be used to execute snmp
    commands and the list from which it start the iteration of every partition,
    it has no arguments and no return values
    """
    global SESSION, hrPartitionLabel, prev_pct
    SESSION = netsnmp.Session(Version = 2)
    hrPartitionLabel = get_values('hrPartitionLabel')
    for i in hrPartitionLabel:
        prev_pct[i] = 0

def get_values(table):
    """
        Function that returns the values especified in a table
    @arg table - the table from which we want the values
    @return - a list containing every value
    """
    global SESSION
    result = netsnmp.Varbind(table)
    resultlist = netsnmp.VarList(result)
    return SESSION.walk(resultlist)

def get_next(value):
    """
        Function that returns the values especified in a element
    @arg value - the value from which we want the result
    @return - a list containing this result
    """
    global SESSION
    result = netsnmp.Varbind(value)
    resultlist = netsnmp.VarList(result)
    return SESSION.get(resultlist)[0]

def normalize_rt():
    global REFRESH_TIME
    if REFRESH_TIME < 5:
        REFRESH_TIME = 5
    elif REFRESH_TIME > 1200:
        REFRESH_TIME = 1200

def populate_dictionary():
    """
        This function receives no arguments and returns no values, all it does
    is modify the current dictionary with the mesurements of every partition
    """
    global hrPartitionLabel, DICT, REFRESH_TIME, prev_pct
    DICT.clear()
    index = 1
    for i in hrPartitionLabel:
        hrPartitionFSIndex = get_values('hrPartitionFSIndex')
        fs_index = int(hrPartitionFSIndex[index-1])
        if fs_index > 0:
            fss_index = int(get_next('hrFSStorageIndex.' + str(fs_index)))
            storageSize = int(get_next('hrStorageSize.' + str(fss_index)))
            storageUsed = int(get_next('hrStorageUsed.' + str(fss_index)))
            free_pct = ((storageSize - storageUsed) / float(storageSize)) * 100
            pct_change = free_pct - prev_pct[i]
            prev_pct[i] = free_pct
            DICT[i] = {
                'hrPartitionFSIndex': int(hrPartitionFSIndex[index-1]),
                'hrFSMountPoint'    : get_next('hrFSMountPoint.' + str(fs_index)),
                'hrFSStorageIndex'  : fss_index,
                'hrStorageAllUnits' : int(get_next('hrStorageAllocationUnits.' + str(fss_index))),
                'hrStorageSize'     : storageSize,
                'hrStorageUsed'     : storageUsed,
                'freeSpace'         : storageSize - storageUsed,
                'freeSpacePct'      : free_pct,
                'pct_change'        : pct_change
            }
        index += 1

"""
    The following functions make everthing pretier
"""
def center(x, string):
    return (x - len(str(string)))/2
def adjust(value):
    if value < 1024:
        return str(float(value)) + ' Bytes'
    elif value / 1024 < 1024:
        return str(float(value/1024)) + ' KBytes'
    elif value / 1024 / 1024 < 1024:
        return str(float(value/1024/1024)) + ' MBytes'
    elif value / 1024 / 1024 / 1024 < 1024:
        return str(float(value/1024/1024/1024)) + ' GBytes'
    else:
        return str(float(value/1024/1024/1024/1024)) + ' TBytes'
def adjust_t(value):
    if value < 60:
        return str(round(value, 3)) + ' seconds'
    elif value / 60 < 60:
        return str(round(value/60, 3)) + ' minutes'
    else:
        return str(round(value/60/60, 3)) + ' hours'

def pbar(window):
    """
        Creates a fancy window on which we display the values
    """
    global EXIT, REFRESH_TIME, DICT, prev_pct
    try:
        while not EXIT:
            unchanged = True
            thread.start_new_thread(populate_dictionary, ( ))
            y,x = window.getmaxyx()

            window.clear()
            window.border(0)
            window.addstr(1, center(x, "partitions"), "Partitions", curses.A_STANDOUT)
            printline = 3
            for i in DICT:
                window.addstr(printline, center(x,str(i)), str(i), curses.A_BOLD)

                printline += 1
                s = "Partition Mounting Point: " + str(DICT[i]['hrFSMountPoint'])
                window.addstr(printline, center(x, s), s)

                printline += 1
                s = "Total Space: "
                tot = DICT[i]['hrStorageSize'] * DICT[i]['hrStorageAllUnits']
                s += adjust(tot)
                window.addstr(printline, center(x, s), s)

                printline += 1
                s = "Used Space: "
                used = DICT[i]['hrStorageUsed'] * DICT[i]['hrStorageAllUnits']
                s += adjust(used)
                window.addstr(printline, center(x, s), s)

                printline += 1
                s = "Free Space: "
                free = DICT[i]['freeSpace'] * DICT[i]['hrStorageAllUnits']
                s += adjust(free)
                free_pct = DICT[i]['freeSpacePct']
                s2 = ' ['+ str(round(free_pct,3)) + '%]'
                window.addstr(printline, center(x, s+s2), s)
                if free_pct < 15:
                    window.addstr(printline, center(x, s+s2)+len(s), s2, curses.A_BLINK)
                else:
                    window.addstr(printline, center(x, s+s2)+len(s), s2)


                printline += 1
                s = "Percentage Change: "
                pct_change = DICT[i]['pct_change']
                s += ' ['+ str(round(pct_change, 5)) + '%]'
                window.addstr(printline, center(x, s), s)
                printline += 3

                if free_pct < 15:
                    REFRESH_TIME = 60
                if unchanged:
                    if pct_change < 0:
                        REFRESH_TIME /= 2
                    else:
                        REFRESH_TIME *= 2
                    unchanged = False
                normalize_rt()

            s = " Refreshing every " + adjust_t(REFRESH_TIME) + " "
            window.addstr(y-1, center(x, s), s)
            window.refresh()
            time.sleep(REFRESH_TIME)
    except KeyboardInterrupt:
        EXIT = True
    except:
        print "Error occurred!"

init_session()
curses.wrapper(pbar)

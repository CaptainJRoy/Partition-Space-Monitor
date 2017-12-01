import netsnmp, thread, time
import curses


SESSION = 0
hrPartitionLabel = 0

DICT = {}
REFRESH_TIME = 5
EXIT = False

def init_session():
    """
        This function initializes the session that will be used to execute snmp
    commands and the list from which it start the iteration of every partition,
    it has no arguments and no return values
    """
    global SESSION, hrPartitionLabel
    SESSION = netsnmp.Session(Version = 2)
    hrPartitionLabel = get_values('hrPartitionLabel')

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

def populate_dictionary():
    """
        This function receives no arguments and returns no values, all it does
    is modify the current dictionary with the mesurements of every partition
    """
    global hrPartitionLabel, DICT
    DICT.clear()
    index = 1
    for i in hrPartitionLabel:
        hrPartitionFSIndex = get_values('hrPartitionFSIndex')
        fs_index = int(hrPartitionFSIndex[index-1])
        if fs_index > 0:
            fss_index = int(get_next('hrFSStorageIndex.' + str(fs_index)))
            storageSize = int(get_next('hrStorageSize.' + str(fss_index)))
            storageUsed = int(get_next('hrStorageUsed.' + str(fss_index)))
            DICT[i] = {
                'hrPartitionFSIndex': int(hrPartitionFSIndex[index-1]),
                'hrFSMountPoint'    : get_next('hrFSMountPoint.' + str(fs_index)),
                'hrFSStorageIndex'  : fss_index,
                'hrStorageAllUnits' : int(get_next('hrStorageAllocationUnits.' + str(fss_index))),
                'hrStorageSize'     : storageSize,
                'hrStorageUsed'     : storageUsed,
                'freeSpace'         : storageSize - storageUsed,
                'freeSpacePct'      : ((storageSize - storageUsed) / float(storageSize)) * 100
            }
        index += 1

"""
    The following functions make everthing pretier
"""
def center(x, string):
    return (x - len(str(string)))/2
def adjust(value):
    if value < 1024:
        return str(round(float(value), 2)) + ' Bytes'
    elif value / 1024 < 1024:
        return str(round(float(value/1024), 2)) + ' KBytes'
    elif value / 1024 / 1024 < 1024:
        return str(round(float(value/1024/1024), 2)) + ' MBytes'
    elif value / 1024 / 1024 / 1024 < 1024:
        return str(round(float(value/1024/1024/1024), 2)) + ' GBytes'
    else:
        return str(round(float(value/1024/1024/1024/1024), 2)) + ' TBytes'
def adjust_t(value):
    if value < 60:
        return str(round(float(value), 2)) + ' seconds'
    elif value / 60 < 60:
        return str(round(float(value/60), 2)) + ' minutes'
    else:
        return str(round(float(value/60/60), 2)) + ' hours'

def pbar(window):
    """
        Creates a fancy window on which we display the values
    """
    global EXIT, REFRESH_TIME, DICT
    try:
        while not EXIT:
            thread.start_new_thread(populate_dictionary, ( ))
            time.sleep(REFRESH_TIME)
            y,x = window.getmaxyx()

            window.clear()
            window.border(0)
            window.addstr(1, center(x, "partitions"), "Partitions")
            printline = 3
            for i in DICT:
                window.addstr(printline, center(x,str(i)), str(i))

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
                s += ' ['+ str(round(free_pct, 2)) + '%]'
                window.addstr(printline, center(x, s), s)

                printline += 3

            s = "Refreshing every " + adjust_t(REFRESH_TIME)
            window.addstr(y-1, center(x, s), s)
            window.refresh()
    except KeyboardInterrupt:
        EXIT = True
    except:
        print "Error occurred!"


init_session()
curses.wrapper(pbar)

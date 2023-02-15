#!/bin/bash

#replayEQ - version 1.4

# send a test message into the EEW system

PROGRAM=`basename $0`
SCRIPTS=`dirname $0`
cd `dirname $0`/..
APPDIR=`pwd`
EVENTIDFILE=$SCRIPTS/nextevent.id
SCENARIO_FILE=$APPDIR/scenarios.dat

HOST=localhost
port=61613
execProg="userdisplay"
TEST=0
verbose=1
scenario=""
message_type=""
category="test"
id=0
user="ShakeOut"
pass="ubevW7gX"
topic=""
EXTRA=""
delay=0
list_only=0
file=""
fileSuffix=""
time=`date +%s`
instance="$LOGNAME@$HOSTNAME"
orig_sys="$PROGRAM"
timestamp="now"
orig_time="now-5"

function get_id {
    [[ ! -f "$EVENTIDFILE" ]] && echo 100 > $EVENTIDFILE
    chmod -f a+rw $EVENTIDFILE
    local _index
    read _index < $EVENTIDFILE
    echo $_index
}
function next_id {
    [[ ! -f "$EVENTIDFILE" ]] && echo 100 > $EVENTIDFILE
    chmod -f a+rw $EVENTIDFILE
    local _index
    read _index < $EVENTIDFILE
    printf "%d" $(( _index+1 )) > $EVENTIDFILE
    echo $_index
}
function prev_id {
    [[ ! -f "$EVENTIDFILE" ]] && echo 100 > $EVENTIDFILE
    chmod -f a+rw $EVENTIDFILE
    local _index
    read _index < $EVENTIDFILE
    echo $((_index-1))
}

function usage {
    if [ $# != "" ]; then echo "$*"; fi
    echo "Usage: $PROGRAM [flags] scenario"
    echo "-?            -- this help"
    echo "-v | -q       -- increase or decrease verbosity level ($verbose)"
    echo "-n scenario   -- override scenarios ($scenario)"
    echo "-e execProg   -- override target execution system ($execProg)"
    echo "-h host       -- override host ($HOST)"
    echo "-P port       -- override port ($port)"
    echo "-u user       -- override user ($user)"
    echo "-p pass       -- override password ($pass)"
    echo "-t topic      -- override topic ($topic)"
    echo "-i id         -- override id ($(get_id))"
    echo "-f eventfile  -- play the specified file ($file)"
    echo "-M type       -- override message type ($message_type)"
    echo "-C cat        -- override category ($category)"
    echo "-S file       -- override scenario file ($SCENARIO_FILE)"
    echo "-X string     -- extra arguments ($EXTRA)"
    echo "-I instance   -- override instance ($instance)"
    echo "-O orig_sys   -- override orig_sys ($orig_sys)"
    echo "-m mag        -- override magnitude"
    echo "-a timestamp  -- override timestamp"
    echo "-b orig_time  -- override orig_time"
    echo "-c            -- cancel event ($(get_id)) using $scenario as template"
    echo "-d seconds    -- initial delay before sending data ($delay)"
    echo "-l            -- list scenarios then quit"
    echo "-T            -- test run only, just show arguments"
    exit
}

if [ $# -eq 0 ]; then usage "No arguments"; fi

while getopts "\?vqn:e:h:P:u:p:t:i:f:M:C:S:X:I:O:m:a:b:cd:lT" opt; do
   case $opt in
      \?) usage;;
      v) verbose=$((verbose + 1));;
      q) verbose=$((verbose - 1));;
      n) scenario=$OPTARG;;
      e) execProg=$OPTARG;;
      h) HOST=$OPTARG;;
      P) port=$OPTARG;;
      u) user=$OPTARG;;
      p) pass=$OPTARG;;
      t) topic=$OPTARG;;
      i) id=$OPTARG;;
      f) file=$OPTARG; scenario="";;
      M) echo "-M is disabled"; usage;; #message_type=$OPTARG;;
      C) echo "-C is disabled"; usage;; #category=$OPTARG;;
      S) SCENARIO_FILE=$OPTARG;;
      X) EXTRA=$OPTARG;;
      I) instance=$OPTARG;;
      O) orig_sys=$OPTARG;;
      m) EXTRA+=" -kv mag=$OPTARG";;
      a) timestamp=$OPTARG;;
      b) orig_time=$OPTARG;;
      c) message_type="delete"; id=$(prev_id);;
      d) delay=$OPTARG;;
      l) list_only=1;;
      T) TEST=1;;
      *) usage "unexpected argument: $opt";;
   esac
done
shift $((OPTIND - 1))

if [ ! $list_only -ne 0 ] && [ -z "$scenario" ] && [ ! -e "$file" ]; then usage "No scenario or file specified!"; fi

if [ $id -eq 0 ]; then id=$(next_id); fi
if [ -n "$message_type" ]; then EXTRA+=" -kv /event_message/@message_type=$message_type"; fi
if [ -n "$category" ]; then EXTRA+=" -kv /event_message/@category=$category"; fi
if [ -n "$instance" ]; then EXTRA+=" -kv /event_message/@instance=$instance"; fi
if [ -n "$orig_sys" ]; then EXTRA+=" -kv /event_message/@orig_sys=$orig_sys"; fi
if [ -n "$id" ]; then EXTRA+=" -kv @id=$id"; fi
if [ -n "$topic" ]; then EXTRA+=" -topic $topic"; fi

if [ $verbose -gt 0 ]; then
echo "verbose=$verbose"
echo "execProg=$execProg"
echo "HOST=$HOST"
echo "port=$port"
echo "SCENARIO_FILE=$SCENARIO_FILE"
echo "scenario=$scenario"
echo "message_type=$message_type"
echo "category=$category"
echo "id=$id"
echo "file=$file"
echo "user=$user"
echo "pass=$pass"
echo "topic=$topic"
echo "EXTRA=$EXTRA"
echo "timestamp=$timestamp"
echo "orig_time=$orig_time"
echo "delay=$delay"
echo "TEST=$TEST"
echo "list_only=$list_only"
fi



SEND2AMQ=$SCRIPTS/send2AMQ.pl
SEND2AMQ_ARGS="-$execProg $scenario -host $HOST -port $port -user $user -pass $pass -kv /event_message/@timestamp=$timestamp -kv /event_message/core_info/orig_time=now-5"

EXTRACT=$SCRIPTS/extractLog.pl
EXTRACT_ARGS="-eewscenario $file"

REPLAYLOG=$SCRIPTS/replayLog.pl
REPLAYLOG_ARGS="- -$execProg -host $HOST -port $port -user $user -pass $pass -kv /event_message/@timestamp=$timestamp -kv /event_message/core_info/orig_time=now-5"

if [[ $file =~ eew$ ]]; then
    CMD="$EXTRACT $EXTRACT_ARGS | $REPLAYLOG $REPLAYLOG_ARGS $EXTRA $*"
elif [[ $file =~ xml$ ]]; then
    CMD="$SEND2AMQ $SEND2AMQ_ARGS $EXTRA $*"
else
    echo "File $file not supported"
    exit
fi
echo -e "\n$CMD\n"

if [ $TEST -ne 0 ]; then echo "skipping, TEST flag is true"; exit; fi

echo "Sleeping for $delay seconds before sending..."
sleep $delay

eval $CMD
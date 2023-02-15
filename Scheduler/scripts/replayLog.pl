#!/usr/bin/perl -w

#replayLog - version 1.2

use strict;

use POSIX qw/strftime/;
use File::Basename;
use Getopt::Long qw(:config no_ignore_case);

my $dirname = dirname($0);
my $SEND2AMQ = "$dirname/send2AMQ.pl";

my $VERSION = "v1.6 2014-03-11";

my $hostname = 0;
my $port = 0;
my $user = "";
my $pass = "";
my $topic = 0;
my $queue = 0;
my $destination = 0;
my $bulk = 0;
my $kv_prefix = "";
my %kv_hash = ();
my $useTimestamps = 0;
my $timeColumn = -1;                # column number to be adjusted, -1 means none
my $window = 20;                    # window around trigger
my $gapTime = "5.000";              # seconds
my $trigger = 0;                    # enable trigger using specified pattern
my $offset = 0;                     # offset for timestamps

my $verbose = 0;                    # verbose flag
my $nosend = 0;                     # dry run, don't connect and send data

my $eewserver = 0;
my $eewscenario = 0;
my $userdisplay = 0;


usage() unless GetOptions(
    "help|h|?"                      => sub { usage(); },
    "VERSION|V"                     => sub { usage($_[0]); },
    "verbose|v+"                    => \$verbose,
    "quiet|q+"                      => sub { $verbose--; },
    "nosend"                        => \$nosend,
    "hostname=s"                    => \$hostname,
    "port=i"                        => \$port,
    "user=s"                        => \$user,
    "password|pwd=s"                => \$pass,
    "Topic|topic=s"                 => \$topic,
    "Queue|queue=s"                 => \$queue,
    "Destination=s"                 => \$destination,
    "timestamps|useTimestamps!"     => \$useTimestamps,
    "timeColumn=i"                  => \$timeColumn,
    "offset=f"                      => \$offset,
    "window=i"                      => \$window,
    "gapTime=f"                     => \$gapTime,
    "trigger=s"                     => \$trigger,
    "bulk"                          => \$bulk,
    "kv_prefix|kvprefix|prefix=s"   => \$kv_prefix,
    "kv_hash|kvhash|kv=s"           => sub { my ($name, $value) = split /=/,$_[1]; 
                                             $kv_hash{$name} = $value; },
    "eewserver"                     => sub { $eewserver = 1;
                                             $useTimestamps = 1; $timeColumn = 8;
                                             $gapTime=16; 
                                             $trigger = "TRIGGER";
                                       },
    "userdisplay"                   => sub { $userdisplay = 1;
                                             $useTimestamps = 1;
                                             $gapTime=30; 
                                             $bulk = 1;
                                    },
    "eewscenario"                   => sub { $eewscenario = 1;
                                             $useTimestamps = 1;
                                             $gapTime=30; 
                                             $bulk = 1;
                                    },
);

print "Program: $0  Version $VERSION\n\n" if $verbose >= 0;

$destination = ($topic) ? "/topic/$topic" : ($queue) ? "/queue/$queue" : 0;

sub usage
{
    print "Program: $0  Version $VERSION\n";
    exit 1 if shift;
    printf "Usage: ". basename $0 ." [args] [file(s)]\n";
    printf "where args: \n";
    printf "-help|-?                        -- this list\n";
    printf "-VERSION                        -- print version and exit\n";
    printf "-verbose|-quiet                 -- increase/decrease verbose level ($verbose)\n";
    printf "-nosend                         -- dry run, don't send ($nosend\n";
    printf "-host name                      -- set host ($hostname)\n";
    printf "-port num                       -- set port ($port)\n";
    printf "-user name                      -- set user ($user)\n";
    printf "-pass str                       -- set user ($pass)\n";
    printf "-Topic topic-name               -- set topic ($topic)\n";
    printf "-Queue queue-name               -- set queue ($queue)\n";
    printf "-Destination destination        -- set destination ($destination)\n";
    printf "-bulk                           -- send contents of file in single message ($bulk)\n";
    printf "-kv_prefix|kvprefix|prefix text -- set kv prefix ($kv_prefix)\n";
    printf "-kv_hash|kvhash|kv name=value   -- enable Xpath procesing using xpath/value pair\n";
    printf "-timestamps|useTimestamps       -- look for timestamps and sleep ($useTimestamps)\n";
    printf "-timeColumn                     -- override timestamp column ($timeColumn)\n";
    printf "-offset n                       -- apply offset to calculated time ($offset)\n";
    printf "-trigger pattern                -- pattern to use for trigger ($trigger)\n";
    printf "-window seconds                 -- window around trigger time ($window)\n";
    printf "-gapTime seconds                -- set max gap between messages ($gapTime)\n";
    printf "-eewserver                      -- shortcut for -trigger=\"TRIGGER\" -useTimestamps -timeColumn=8; -gapTime 16 -Topic eew.alg.onsite.wp.data\n";
    printf "-userdisplay                    -- shortcut for -bulk and other stuff\n";
    printf "-eewscenario                    -- shortcut for -bulk and other stuff\n";
    exit 1;
} # usage

if ($verbose > 0) {
    print "# verbose=$verbose\t\t\tnosend=$nosend\t\tbulk=$bulk\n";
    print "# hostname=$hostname\t\tport=$port\n";
    print "# user=$user\t\t\tpass=$pass\n" if $user ne "" || $pass ne "";
    print "# topic=$topic\t\tqueue=$queue\t\t\tdestination=$destination\n";
    print "# offset=$offset\t\ttimeColumn=$timeColumn\n";
    print "# useTimestamps=$useTimestamps\t\t\twindow=$window\t\tgapTime=$gapTime\t\ttrigger=$trigger\n";
    print "# kv_hash size=" . scalar(keys %kv_hash) . "\t\tkv_prefix=$kv_prefix\n";
    foreach my $key (sort keys(%kv_hash)) {
        print "  $key: $kv_hash{$key}\n";
    }
    print "\n";
}

if (scalar @ARGV == 0) {
    print "No args or file specified.  Use -h for help.\n";
    exit(1);
}

die "No destination, aborting!" if !$destination && !$eewserver && !$userdisplay && !$eewscenario;

    

my $lasttime = 0;
my $timestamp = 0;

# read_timestamp_file() -- reads specified file, returns list of timestamped records
sub read_timestamp_file($) {

    my $filename = shift;
    open FILE, $filename or die "Could not open file $filename for input";

    my @data = ();
    while (my $line = scalar <FILE>) {

        $line =~ s/^\s+//;              # trim leading spaces
        $line =~ s/\s+$//;              # trim trailing spaces
        next if $line =~ m/^#.*$"/;     # skip comments

        print "debug: line=$line\n" if $verbose > 3;

        if ($useTimestamps) {
            ($timestamp, $line) = split(/\|/, $line, 3);
            print "debug: timestamp=$timestamp  line=$line\n" if $verbose > 2;
            next if !$timestamp;
        }
        next if !$line || $line =~ m/^\s+$/;

        push @data, [ ($timestamp, $line) ];
    }
    close FILE;

    return @data;
} # read_timestamp_file


# find_triggers() -- returns timestamp of triggers
sub find_triggers($$) {
    my @data = @{$_[0]};
    my $pattern = $_[1];
    my @triggers = ();

    foreach my $ref (@data) {
        my ($timestamp, $data) = @{$ref};
        if ($data =~ m/$pattern/) {
            print "Found $timestamp, $data\n" if $verbose > 2;
            push @triggers, $timestamp;
        }
    }
    return @triggers;
} # find_triggers


# filter_list() -- returns list of packets that bracket each trigger within a certain window
sub filter_list($$$) {
    my @data = @{$_[0]};
    my @triggers = @{$_[1]};
    my $window = $_[2];

    return () if scalar @triggers == 0;      # return with full list of no triggers

    my @filtered = ();
    my $trigger = shift @triggers;
    printf "#debug: trigger is %0.3f, searching for [%0.3f, %0.3f]\n", $trigger, $trigger - $window, $trigger + $window if $verbose > 1;

    # scan packets
    foreach my $ref (@data) {
        my ($timestamp, $data) = @{$ref};

        # reset trigger when timestamp is greater than window
        if (scalar @triggers > 0 && $timestamp > $trigger + $window) {
            $trigger = shift @triggers;
            printf "#debug: trigger is %0.3f, searching for [%0.3f, %0.3f]\n", $trigger, $trigger - $window, $trigger + $window if $verbose > 1;
            redo;
        } 
        # discard packets if outside of window
        elsif ( abs($timestamp - $trigger) > $window ) {
            print "#debug: discarding $timestamp, $data\n" if $verbose > 1;
            next;
        }

        # save packet
        print "#debug: saving $timestamp, $data\n" if $verbose > 1;
        push @filtered, $ref;

    }
    return @filtered;
} # filter_list

sub pause($)
{
    my $seconds = shift;
    select(undef, undef, undef, $seconds);
}

###################
# main loop
###################

#my %orig_time = ();

my $orig_time = 0;

while (my $filename = shift) {

    last if !$filename;

    print "\nDebug: step 1 -- read file into array...\n\n" if $verbose > 1;

    my @data = read_timestamp_file($filename);
    print "debug: read_timestamp_file returned ". scalar @data ."\n" if $verbose > 1;

    if ($trigger) {
        print "\nDebug: step 2 -- find triggers...\n\n" if $verbose > 1;

        my @triggers = find_triggers(\@data, $trigger);
        print "debug: find_triggers returned ". scalar @triggers ."\n" if $verbose > 1;

        if (scalar @triggers > 0) {
            print "\nDebug: step 3 -- filter packets...\n\n" if $verbose > 1;

            @data = filter_list(\@data, \@triggers, $window);
            print "debug: filter_list returned ". scalar @data ."\n" if $verbose > 1;
        } else {
            next;
        }
    }

    print "\nDebug: step 4 -- send filtered list with delays...\n\n" if $verbose > 1;


    # GET ORIG_TIME AND KEEP ONE VALUE FOR IT - AGG 12/03/2018
    if ($eewscenario) {
        my @time = gmtime(time - 1);
        $orig_time = strftime("%FT%T.000Z", @time);		        
    }

    foreach my $ref (@data) {

        my ($timestamp, $data) = @{$ref};

        print "orig_time = $orig_time\n";

#        my ($evid, $orig_time);
        my $evid;
        # look for orig time
        if ($userdisplay or $eewscenario) {

        ($evid = $data) =~ s/^.*\/(.+)_\d+\.xml/$1/;
#       TAKE OUT CODE HERE, IT WILL RESET THE ORIG_TIME FOR EACH MESSAGE - AGG 12/03/2018
#            if (!exists $orig_time{$evid}) {
#                my @time = gmtime(time - 1);
#                $orig_time{$evid} = strftime("%FT%T.000Z", @time);		
#            } 
#            $orig_time = $orig_time{$evid};
            
#            print "evid=$evid: $timestamp => $orig_time{$evid}\n" if $verbose > 1;

        }

        # calculate delta, apply max gap time, use zero the first time
        $lasttime = $timestamp if $lasttime == 0;
        my $delta = sprintf "%0.3f", abs($timestamp - $lasttime);
        $delta = $gapTime if $delta > $gapTime;
	$delta -= 1.0;   # assume 1 second delay to call send2AMQ, connect, send and exit
        print "Sleeping for " . $delta . " seconds\n" if $verbose >= 0;
        pause($delta) ;#if !$nosend;

        if ($timeColumn > -1) {
            my @line = split(" ", $data);
            my $otime = $line[$timeColumn] % 86400 + $offset;
            my $dtime = int($timestamp) - $otime;
            my $atime = time - $dtime;# + $offset;
            print "ndata=$data, otime=$otime dtime=$dtime atime=$atime\n" if $verbose >= 1;
            $line[$timeColumn] = $atime;
            $data = join(" ", @line);
        }

        print "$timestamp|$data\n" if $verbose >= 0;

        my $cmd = "echo \"$data\" | $SEND2AMQ -";
#        if ($userdisplay) {
#            $cmd = "$SEND2AMQ $data -userdisplay -v -v";
#            $cmd .= " -kv_prefix $kv_prefix" if $kv_prefix ne "";
#            foreach my $key (sort keys(%kv_hash)) {
#                $cmd .= " -kv $key=$kv_hash{$key}";
#            }
#            $cmd .= " -kv \@id=TEST_$evid" if !exists($kv_hash{'@id'});
#            $cmd .= " -kv \@timestamp=now" if !exists($kv_hash{'@timestamp'});
#            $cmd .= " -kv orig_time=$orig_time{$evid}" if !exists($kv_hash{'orig_time'});
#        }
        if ($eewscenario) {
            $cmd = "$SEND2AMQ $data -eewscenario -v -v";
            $cmd .= " -kv_prefix $kv_prefix" if $kv_prefix ne "";
            foreach my $key (sort keys(%kv_hash)) {
                $cmd .= " -kv $key=$kv_hash{$key}";
            }
            $cmd .= " -kv \@id=TEST_$evid" if !exists($kv_hash{'@id'});
            $cmd .= " -kv \@timestamp=now" if !exists($kv_hash{'@timestamp'});
            $cmd .= " -kv /event_message/core_info/orig_time=$orig_time" if !exists($kv_hash{'@/event_message/core_info/orig_time'});
        }
        $cmd .= " -eewserver" if $eewserver;
        $cmd .= " -host $hostname" if $hostname;
        $cmd .= " -port $port" if $port;
        $cmd .= " -user $user" if $user ne "";
        $cmd .= " -pass $pass" if $pass ne "";
        $cmd .= " -Queue $queue" if $queue;
        $cmd .= " -Topic $topic" if $topic;
        $cmd .= " -Destination $destination" if $destination;
        printf "cmd=$cmd\n" if $verbose > 1;
        if (!$nosend) {
            my $status = system($cmd);
            if (($status >>= 8) != 0) {
                printf "Unable to send message using $cmd: $status\n";
            }
        }
        $lasttime = $timestamp;

        print "\n" if $verbose > 1;
    }

} # for each file on command line


exit 0;



#!/usr/bin/perl -w

#send2AMQ - version 1.3

use strict;

use POSIX qw/strftime/;
use File::Basename;
use Net::Stomp;                     # for sending ActiveMQ messages using Stomp package
use XML::XPath;                     # for parsing XML
use IO::Socket::SSL;		    # for SSL

use Getopt::Long qw(:config no_ignore_case);

my $VERSION = 'v1.9 2018-09-21 ($Id: send2AMQ.pl 7159 2018-09-21 16:47:12Z ggann $)';

my $hostname = 'localhost';
my $port = 61613;
my $user = "";
my $pass = "";
my $topic = 'eew.test.news.data';
my $queue = 0;
my $destination = 0;
my $bulk = 0;
my $kv_prefix = "";
my %kv_hash = ();
my $repeat = 1;
my $delay = 0;

my $verbose = 0;                # verbose flag
my $nosend = 0;                 # dry run, don't connect and send data


usage() unless GetOptions(
    "help|h|?"                      => sub { usage(); },
    "VERSION|V"                     => sub { usage($_[0]); },
    "verbose|v+"                    => \$verbose,
    "quiet|q+"                      => sub { $verbose--; },
    "nosend"                        => \$nosend,
    "hostname=s"                    => \$hostname,
    "user=s"                        => \$user,
    "password|pwd=s"                => \$pass,
    "port=i"                        => \$port,
    "Topic|topic=s"                 => \$topic,
    "Queue|queue=s"                 => \$queue,
    "Destination|destination=s"     => \$destination,
    "bulk"                          => \$bulk,
    "repeat=i"                      => \$repeat,
    "delay=i"                       => \$delay,
    "kv_prefix|kvprefix|prefix=s"   => \$kv_prefix,
    "kv_hash|kvhash|kv=s"           => sub { my ($name, $value) = split /=/,$_[1]; 
                                             $name = $kv_prefix . $name if $name !~ m/^\//;
                                             $kv_hash{$name} = $value; },
    "eewserver"                     => sub { $topic = "eew.alg.onsite.wp.data"},
    "eewscenario"                   => sub { $topic = "eew.sys.dm.data"},
    "userdisplay"                   => sub { $topic = "eew.sys.dm.data";
                                             $kv_prefix="/event_message/core_info/" },
);

print "Program: $0  Version $VERSION\n\n" if $verbose >= 0;

if (!$destination) {
    $destination = ($topic) ? "/topic/$topic" : ($queue) ? "/queue/$queue" : 0;
}

sub usage
{
    print "Program: $0  Version $VERSION\n";
    exit 1 if shift;
    printf "Usage: ". basename $0 ." [args] [file(s)]\n";
    printf "where args: \n";
    printf "-help|-?                        -- this list\n";
    printf "-VERSION                        -- print version and exit\n";
    printf "-verbose|-quiet                 -- increase/decrease verbose level ($verbose)\n";
    printf "-nosend                         -- dry run, don't send ($nosend)\n";
    printf "-host name                      -- set host ($hostname)\n";
    printf "-port num                       -- set port ($port)\n";
    printf "-user name                      -- set user ($user)\n";
    printf "-pass str                       -- set user ($pass)\n";
    printf "-topic topic-name               -- set topic ($topic)\n";
    printf "-queue queue-name               -- set queue ($queue)\n";
    printf "-destination destination        -- set destination ($destination)\n";
    printf "-bulk                           -- send contents of file in single message ($bulk)\n";
    printf "-repeat num                     -- set to number of iterations to send file - 0 for infinite ($repeat)\n";
    printf "-delay num                      -- set delay for sending a file ($delay)\n";
    printf "-kv_prefix|kvprefix|prefix text -- set kv prefix ($kv_prefix)\n";
    printf "-kv_hash|kvhash|kv name=value   -- enable Xpath procesing using xpath/value pair\n";
    printf "-eewserver                      -- shortcut for -Topic eew.alg.onsite.wp.data\n";
    printf "-eewscenario                    -- shortcut for -Topic eew.sys.dm.data\n";
    printf "-userdisplay                    -- shortcut for -Topic eew.sys.dm.data -kv_prefix /event_message/core_info/\n";
    exit 1;
} # usage

if ($verbose > 0) {
    print "# verbose=$verbose\t\t\t\tnosend=$nosend\t\tbulk=$bulk\n";
    print "# hostname=$hostname\t\t\tport=$port\n";
    print "# repeat=$repeat\t\t\tdelay=$delay\n";
    print "# user=$user\t\t\tpass=$pass\n" if $user ne "" || $pass ne "";
    print "# topic=$topic\t\tqueue=$queue\t\t\tdestination=$destination\n";
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

die "No destination, aborting!" if !$destination;

my $client;
if (!$nosend) {
    print "Connecting to $hostname:$port, destination=$destination\n" if $verbose >= 0;
    $client = Net::Stomp->new( { hostname => $hostname, port => $port, ssl => 1 } ) ||
        die "Unable to bind to $hostname:$port";

        my %auth = ();
        $auth{'login'} = $user if $user ne "";
        $auth{'passcode'} = $pass if $pass ne "";
        print "connecting activemq as $user/$pass\n" if $verbose > 1;
        $client->connect(\%auth) ||
            die "Unable to connect to $hostname:$port as $user/$pass";
}
    
sub send_message($) {
    if (!$nosend) {
        $client->send( { destination => $destination, body => shift })
        || die "Unable to send message to $destination";
    }
} # sub send_message

sub send_messages($) {
    my $filename = shift;
    open FILE, $filename or die "Could not open file $filename for input";

    while (my $line = scalar <FILE>) {

        $line =~ s/^\s+//;              # trim leading spaces
        $line =~ s/\s+$//;              # trim trailing spaces
        next if $line =~ m/^#.*$"/;     # skip comments

        send_message($line);
        print "$line\n" if $verbose > 2;
    }
    close FILE;

} # sub send_messages

sub read_bulk_file($) {
    my $filename = shift;
    open FILE, $filename or die "Could not open file $filename for input";

    my $text = <FILE>;
    while (my $line = scalar <FILE>) {
            $text .= $line;
    }
    close FILE;

    print "debug: text=$text\n" if $verbose > 2;

    return $text;
} # sub read_bulk_file

sub parse_xml_file($) {
    my $filename = shift;

    my $xp = XML::XPath->new( filename => $filename );
    my $xml = $xp->find("/")->get_node(1);
    my $text = $xml->toString();
    print "debug: original XML=$text\n" if $verbose > 3;

    my $scenarioIDText = $xp->getNodeText("/event_message/core_info/\@id");
    my $concatIDText = "";

    foreach my $key (keys(%kv_hash)) {
        my $oldVal = $xp->getNodeText($key);
        my $newVal = $kv_hash{$key};
	if ($key =~ m/id/) {
	    $concatIDText = $newVal . "_$scenarioIDText";   	    
	}
        if ($newVal =~ m/now-5/) {
            my @time = gmtime(time - 5);
            $newVal = strftime("%FT%T.000Z", @time) 
        }
        if ($newVal =~ m/now/) {
            my @time = gmtime(time);
            $newVal = strftime("%FT%T.000Z", @time) 
        }
        $xp->setNodeText($key, $newVal);
        print "Changed value for key $key from $oldVal to $newVal\n" if $verbose > 1;
    }
    $xp->setNodeText("/event_message/core_info/\@id", $concatIDText);
    $text = $xml->toString();
    print "debug: revised XML=$text\n" if $verbose > 2;

    return $text;
} # sub parse_xml_file


###################
# main loop
###################

while (my $filename = shift) {

    my $i = 0; 
    last if !$filename;

    for($i=0; $i < $repeat; $i = $i + 1) {

        if ($bulk) {
            my $text = read_bulk_file($filename);
            send_message($text);
        } elsif (keys(%kv_hash) > 0) {
            my $text = parse_xml_file($filename);
            send_message($text);
        } else {
            send_messages($filename);
        }
        sleep($delay);
    }
    print "\n" if $verbose > 1;
} # for each file on command line


if (!$nosend) {
    print "disconnecting\n" if $verbose > 2;
    $client->disconnect;
}

exit 0;


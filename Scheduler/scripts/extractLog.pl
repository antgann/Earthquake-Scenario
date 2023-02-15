#!/usr/bin/perl -w

use strict;
use File::Basename;
use Getopt::Long qw(:config no_ignore_case);
use Time::Local;

my $VERSION = "v1.5 2013-05-29";

my $verbose = 0;          # verbose flag
my $pattern = '(.+)(.*)';
my $subst = '$1';
my $startTime = 0;
my $endTime = 0;
my $duration = 0;
my $prefix = 0;        # directory path for playing back files


usage() unless GetOptions(
    "help|h|?"      => sub { usage(); },
    "VERSION|V"     => sub { usage($_[0]); },
    "verbose|v+"    => \$verbose,
    "quiet+"        => sub { $verbose--; },
    "Pattern=s"     => \$pattern,
    "Subst=s"       => \$subst,
    "prefix=s"      => \$prefix,
    "eewserver"     => sub { $verbose=-1; $pattern = '(\d+:\d+:\d+:\d+).*(TSMETHOD.*)].*'; $subst = '$1|$2'; },
    "userdisplay"   => sub { $verbose=-1; $pattern = '(\d+)\s+(.+)'; $subst = '$1|$2'; $prefix = "./"},
    "eewscenario"   => sub { $verbose=-1; $pattern = '(\d+)\s+(.+)'; $subst = '$1|$2'; $prefix = "./"},
    "startTime|s=s" => sub { $startTime = parseTime($_[1]); },
    "endTime|e=s"   => sub { $endTime = parseTime($_[1]); },
    "duration=s"    => sub { $duration = parseTime($_[1]); },
);

print "Program: $0  Version $VERSION\n\n" if $verbose >= 0;

sub usage
{
    print "Program: $0  Version $VERSION\n";
    exit 1 if shift;
    printf "Usage: ". basename $0 ." [args] [file(s)]\n";
    printf "where args: \n";
    printf "-help|-?                        -- this list\n";
    printf "-VERSION                        -- print version and exit\n";
    printf "-verbose|-quiet                 -- increase/decrease verbose level ($verbose)\n";
    printf "-Pattern s                      -- set pattern for maching\n";
    printf "-Subst s                        -- set substitution string\n";
    printf "-eewserver                      -- assume eewserver dd:dd:dd:ddd TSMETHOD pattern\n";
    printf "-userdisplay                    -- assume userdisplay .eew files referencing xml files\n";
    printf "-eewscenario                    -- assume userdisplay .eew files referencing xml files for eewscenario sys usage\n";
    printf "-startTime hh:mm:ss[:ms]|sss    -- specify start time in either hhmmss or seconds\n";
    printf "-endTime hh:mm:ss[:ms]|sss      -- specify end time in either hhmmss or seconds\n";
    printf "-duration hh:mm:ss[:ms]|sss     -- specify duration from trigger time in either hhmmss or seconds\n";
    exit 1;
} # usage


if ($verbose > 0) {
    print "# verbose=$verbose\n";
    print "# pattern=$pattern\t\tsubst=$subst\n";
    print "# startTime=$startTime\tendtime=$endTime\tduration=$duration\n";
    print "# prefix=$prefix\n";
}


if (scalar @ARGV == 0) {
    print "No args or file specified.  Use -h for help.\n";
    exit(1);
}

while (my $filename = shift) {

    if ($filename) {
        open FILE, $filename or die "Could not open file $filename for input";

        $prefix = dirname($filename) . "/" if $prefix && !($filename =~ m/-/);

        my $triggerTime = 0;
        while (<FILE>) {
            s/^\s+//;   # trim leading spaces
            s/\s+$//;   # trim trailing spaces
            my $line = $_;
            printf "# Before: $line\n" if $verbose > 2;
            next if !($line =~ s/$pattern/$1|$2/);
            print "# filtered: $1 : $2\n" if $verbose > 1;
            next if !$1 || !$2;
            my $seconds = parseTime($1);
            print "# seconds=$seconds\n" if $verbose > 1;
            my $text = $2;
            $text = $prefix . $text if $prefix;

            # check for start, end and duration constraints
            next if $startTime > 0 && $seconds < $startTime;
            last if $endTime > 0 && $seconds > $endTime;
            $triggerTime = $seconds if $triggerTime == 0; 
            next if $duration > 0 && $seconds - $triggerTime > $duration;

            printf "%0.3f|%s\n", $seconds, $text;

            print "\n" if $verbose > 1;
        }

        close FILE;
    }
} # for each file on command line

exit 0;

# function parseTime
# input: hh:mm:ss:fff
sub parseTime {
    my $seconds = -1;
    my $arg = shift;
    if ($arg =~ m/:/) {
        $arg .= ":000";  # append fractional seconds just in case
        my @timestamp = split /:/, $arg;
        $seconds = ($timestamp[0] * 3600 + $timestamp[1] * 60 + $timestamp[2]) + ($timestamp[3] / 1000);
    } elsif ($arg > 365 * 86400) {    # convert unix time in milliseconds to seconds
        $seconds = $arg / 1000;
    } else {
        $seconds = $arg;
    }

    return $seconds;
}




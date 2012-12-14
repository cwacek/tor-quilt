#!/usr/bin/perl -w
use Time::HiRes qw(usleep);
use List::Util qw(shuffle);
use Getopt::Std;

srand(time);

sub HELP_MESSAGE {
  print STDERR "Start a voip_emul client\n";
  print STDERR "Usage: voip_runner.pl -h <socks_host> -p <socks_port> -t <send_duration>\n";
  print STDERR "                      -D <data_directory> -d <destination_list (comma-sep)>\n";
  print STDERR "                      -S <Torify_script_location>\n";
  print STDERR "\n";
}

getopts("h:p:t:d:D:S:");

if (!defined($opt_h) or !defined($opt_p) 
    or !defined($opt_D) or !defined($opt_d)
    or !defined($opt_t))
{
  HELP_MESSAGE;
  exit 1;
}

my $socks_host = $opt_h;
my $socks_port = $opt_p;

my @dests = shuffle(split(",",$opt_d));
my $datadir = $opt_D;
my $duration = $opt_t;

my $PAUSE_VARIANCE = 5;
my $tmp_file = "";

sleep (int(rand() * $PAUSE_VARIANCE));  # wait for tor client to start

while(1) {
	my $cmd;
  my $ip = shift(@dests);
  push(@dests,$ip); #replace it at the end incase we loop through

  $cmd = "$opt_S $socks_host $socks_port \'voip_emul -c $ip 4500 $duration >> $datadir/voip \' ";
  print "$cmd\n";
  system("$cmd");

  my $pause = int(rand() * $PAUSE_VARIANCE);
	sleep $pause;
}

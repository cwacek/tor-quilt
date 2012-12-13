#!/usr/bin/perl -w
use Time::HiRes qw(usleep);
use List::Util qw(shuffle);
use Getopt::Std;

srand(time);

sub HELP_MESSAGE {
  print STDERR "Start a curl client\n";
  print STDERR "Usage: curl_runner.pl -h <socks_host> -p <socks_port> [-a <client_active_time>] \n";
  print STDERR "                      -D <data_directory> -d <destination_list (comma-sep)> [-b]\n";
  print STDERR "\n";
  print STDERR "     -a <client_active_time> \t The amount of seconds a client should be active. It alternates\n";
  print STDERR "                                sleep and active time, with sleeps lasting 60 seconds.\n";
  print STDERR "                                (Default: 300)\n";
  print STDERR "\n";
  print STDERR "     -b                      \t Flag designating whether or not this should be a bulk client\n";
}

our $opt_b;

getopts("h:p:a:bd:D:");

if (!defined($opt_h) or !defined($opt_p) 
    or !defined($opt_D) or !defined($opt_d))
{
  HELP_MESSAGE;
  exit 1;
}

my $socks_host = $opt_h;
my $socks_port = $opt_p;

my @dests = split(",",$opt_d);
my $datadir = $opt_D;
my $bulk = defined($opt_b) ? 1 : 0;

my $MAX_PAUSE_HTTP = 11;
my $MAX_PAUSE_BULK = 0;
my $CLIENT_SLEEP_SECS = 60;
my $CLIENT_ACTIVE_SECS = (defined($opt_a) ? $opt_a : 300);
my $MAX_HTTP_STREAMS = 0;
my $MAX_BULK_STREAMS = 0;
my $tmp_file = "";

my @http_files = ( "250KB.file", "500KB.file", "750KB.file");
my @bulk_files = ("1MB.file", "3MB.file",  "5MB.file");

sub select_target($;\@){
  my ($if,$dests) = @_;

  if ($if < 0){
    my $tmp = shift shuffle($dests);
    push @$dests, $tmp;
    return "$tmp";
  } else {
    return "10.0.".int($if/256).".".int($if%256);
  }
}

sub pick {
  my @files = @_;
  my $filename = "";
  my $r = rand();

  if($r < 0.33) {
    $filename = $files[2];
  } elsif($r < 0.66) {
    $filename = $files[1];
  } else {
    $filename = $files[0];
  }
  return "$filename";
}

if(!defined($socks_host) || !defined($socks_port) || !defined($bulk)) {
  print STDERR "Arguments: <socks host> <socks port> <bulk ?>\n";
  exit;
}

#Start with a random sleep length.
my @state = ("Sleeping",rand($CLIENT_SLEEP_SECS));
sleep(rand($CLIENT_SLEEP_SECS));
my $time_to_sleep = time + $CLIENT_ACTIVE_SECS;

while (1){
  if (!$bulk and ($time_to_sleep < time)){
    sleep($CLIENT_SLEEP_SECS);
    $time_to_sleep = time + $CLIENT_ACTIVE_SECS;
  }

  my $filename = "";
  my $url = "";
  my $num_streams = 0;

  if($bulk == 0) {
    $num_streams = 1 + int(rand($MAX_HTTP_STREAMS));
  } else {
    $num_streams = 1 + int(rand($MAX_BULK_STREAMS));
  }

  for(my $i = 0; $i < $num_streams; $i++) {
    my $size = 0;
    if($bulk == 0) {
      $filename = pick(@http_files);
#$filename = "300KB.file";
    } else {
      $filename = pick(@bulk_files);
#$filename = "5MB.file"
    }
    $url = select_target(-1,@dests);
  }
  my $time = time;

  my $cmd = qq(curl --socks4 $socks_host:$socks_port -o /dev/null -w '$time Connect: %{time_connect} TTFB: %{time_starttransfer} Total time: %{time_total} Size: %{size_download}\n' $url/$filename 2>/dev/null >> $datadir/curl);
#my $cmd = "".$conf->get_base_path."/tools/torify.pl $socks_host $socks_port \'".$conf->get_base_path."/tools/pget.py < $tmp_file 2>> /tmp/tor-client-$socks_host:$socks_port/wget\'";
  print "$cmd\n";
  system("$cmd");


  my $pause = 0;
  if($bulk == 0) {
    $pause = 1 + int(rand() * $MAX_PAUSE_HTTP);
  } else {
    $pause = 1 + int(rand() * $MAX_PAUSE_BULK);
  }
  sleep $pause;
}                                                  

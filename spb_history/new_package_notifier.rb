#!/usr/bin/env ruby

require 'fileutils'
require 'json'
require 'base64'
require 'pp'
require 'yaml'
require 'mechanize'
require 'net/smtp'

puts "in new_package_notifier.rb!"

server = "mx.fhcrc.org"
from_name = "Bioconductor Build System"
from_addr = "biocbuild@fhcrc.org"
to = ['dtenenba@fhcrc.org', 'lg390@cam.ac.uk'] 



if ARGV.length < 1
    puts "oops, no arg"
    exit
end

json = Base64.decode64(ARGV.first)
obj = JSON.parse(json)


if obj["client_id"] =~ /^single_package_builder_autobuild/
    issue_id = obj["client_id"].split(":")[1]
    trackerfile = "#{File.dirname(__FILE__)}/tracker.yaml"
    unless File.exists? trackerfile
        puts "oops, no tracker.yaml"
        exit
    end
    url = "http://tracker.fhcrc.org/roundup/bioc_submit/issue#{issue_id}"
    cfg = YAML::load(File.open("tracker.yaml"))
    @agent = Mechanize.new
    page = @agent.post(url, {
        "__login_name" => cfg['username'],
        "__login_password" => cfg['password'], 
        "__came_from" => url,
        "@action" => "login"
    })
    rows = page.search("table.files tr")
    title = page.search("title").text.split(":").last.split("-").first.strip
    if rows.length == 3 # this is the first upload of a new package
        message = <<"MESSAGE_END"
From: #{from_name} <#{from_addr}>
To: #{to.join ", "}
Subject: New package notification: #{title}

A new package has been added to the Bioconductor tracker.

The package is called #{title} and can be found at:

#{url}

This is an automated message. Please do not reply to it.

If you no longer want to receive these notifications, please 
contact maintainer@bioconductor.org.

MESSAGE_END
        Net::SMTP.start('mx.fhcrc.org') do |smtp|
            smtp.send_message message, from_addr, to
        end
        puts "sent email notification about #{title}"
    else
        puts "not the first appearance of this package"
    end
else
    puts "not a notification we are interested in"
end
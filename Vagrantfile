# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
  config.vm.box = "bento/ubuntu-14.04"
  config.vm.network "private_network", ip: "192.168.33.10"
  config.vm.synced_folder ".", "/auto_grant"
  config.vm.provision "shell" do |s|
    s.path = "provision/setup.sh"
  end
end

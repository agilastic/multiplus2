#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import locale, os
from time import gmtime, strftime
from datetime import *
import datetime
import sys
import time
import logging
import requests, time, sys
from requests.auth import HTTPBasicAuth
from pprint import pprint


#locale.setlocale(locale.LC_ALL, 'de_DE.utf-8')
#locale.setlocale(locale.LC_NUMERIC, 'de_DE.utf-8')


multiplus_max_power  =  3000  # Charge
multiplus_min_power  = -3000  # Feed
bat_min_voltage = 49
bat_max_voltage = 58
port = '/dev/serial/by-id/usb-VictronEnergy_MK3-USB_Interface_HQ2245XNCCN-if00-port0'




class MultiplusDaemon():
  def run(self):
    global multiplus_max_power 
    global multiplus_min_power
    global bat_min_voltage
    global bat_max_voltage
    global port
    log_file = '/var/log/multiplus.log'
    Path('').touch()
    logging.basicConfig(filename=log_file, level=logging.DEBUG,
        format='%(asctime)s %(levelname)-8s %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
    logging.info('run...')

    while True:
      log_file_size = os.path.getsize(log_file)
      if log_file_size > 50000000:
        logging.info(f'log file > 50000000')
        f = open(log_file, "w")
        f.write('')
        f.close()      
      try:
        mp2 = MultiPlus2(port)
        grid_sum = int(float(requests.get("http://vcloudpihole.home.ebeling-hoppe.de/pv/em-current.json").json()['sum']))         
        t0 = time.perf_counter()
        mp2.update()    # read all information
        print(time.perf_counter() - t0, mp2.data)
        time.sleep(0.5)
        info = mp2.vebus.read_snapshot()
        bat_u = info['bat_u']
        bat_i = info['bat_i']
        bat_p = info['bat_p'] # + Charge / - Feed
        soc = info['soc']
        logging.info("SOC: " + str(soc))
        logging.info("bat_p: " + str(bat_p))
        logging.info("bat_i: " + str(bat_i))
        logging.info("bat_u: " + str(bat_u))                
        time.sleep(1)
      except Exception as e:
        logging.info(e)        
        logging.info('Fehler beim Abrufen der Daten von Multiplus')
        time.sleep(60) # wait
        continue
      try:
        if bat_u >= bat_min_voltage and bat_u < bat_max_voltage:    
          setpoint = (-1) * (grid_sum + bat_p)# Neues Limit in Watt
          # check for upper limit
          if setpoint > multiplus_max_power:
            setpoint = multiplus_max_power
            logging.info(f'Setpoint auf Maximum: {multiplus_max_power} W')
          # check for lower limit
          elif setpoint < multiplus_min_power:
            setpoint = multiplus_min_power
            logging.info(f'Setpoint auf Minimum: {multiplus_max_power} W')
          else:
            logging.info(f'Setpoint berechnet: {round(grid_sum, 1)} W + {round(bat_p, 1)} W  = {round(setpoint, 1)} W')
            
          if setpoint != bat_p:
            logging.info(f'Setze Inverterlimit von {round(bat_p, 1)} W auf {round(setpoint, 1)} W... ')
            try:
              mp2.vebus.set_power(setpoint)   # negative value is feed to grid
                                                    # positive value is charge battery
              time.sleep(1) # wait
            except Exception as e:
              logging.info(e)
              logging.info('Fehler beim Senden der Konfiguration')
        elif bat_u < bat_min_voltage:
          try:          
            logging.info('battery out of voltage range. Set 50W charging... ') 
            mp2.vebus.set_power(50)   # positive value is charge battery
            time.sleep(60*15) # wait
          except Exception as e:
            logging.info(e)
            logging.info('Fehler beim Senden der Konfiguration') 
        elif bat_u > bat_max_voltage:
          try:
            logging.info('battery out of voltage range. Set -50W feed-in... ')           
            mp2.vebus.set_power(-50)   # negative value is feed to grid
            time.sleep(60*15) # wait
          except Exception as e:
            logging.info(e)
            logging.info('Fehler beim Senden der Konfiguration')  
      except Exception as e:
        logging.info(e)
        logging.info('Fehler beim Senden der Konfiguration')          
   
              

   

if __name__ == '__main__':
    daemon = MultiplusDaemon()
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.run()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print('Unkn own command')
            sys.exit(2)
        sys.exit(0)
    else:
        print('usage: %s start|stop|restart' % sys.argv[0])
        sys.exit(2)


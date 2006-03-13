### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id: __init__.py,v 1.1 2006/03/01 23:26:46 djpham Exp $

phonemodels={ 'LG-G4015 (AT&T)': 'com_lgg4015',
              'LG-C2000 (Cingular)': 'com_lgc2000',
              'LG-VX3200': 'com_lgvx3200',
              'LG-VX4400': 'com_lgvx4400',
              'LG-VX4500': 'com_lgvx4500',
              'LG-VX4600 (Telus Mobility)': 'com_lgvx4600',
              'LG-VX4650 (Verizon Wireless)': 'com_lgvx4650',
              'LG-VX5200 (Verizon Wireless)': 'com_lgvx5200',
              'LG-LX5450 (Alltel)': 'com_lglx5450',
              'LG-VX6000': 'com_lgvx6000',
              'LG-VX6100': 'com_lgvx6100',
              'LG-LG6200 (Bell Mobility)': 'com_lglg6200',
              'LG-VX7000': 'com_lgvx7000',
              'LG-VX8000 (Verizon Wireless)': 'com_lgvx8000',
              'LG-VX8100 (Verizon Wireless)': 'com_lgvx8100',
              'LG-VX9800 (Verizon Wireless)': 'com_lgvx9800',
              'LG-PM225 (Sprint)': 'com_lgpm225',
              'LG-PM325 (Sprint)': 'com_lgpm325',
              'LG-TM520': 'com_lgtm520',
              'LG-VX10': 'com_lgtm520',
              'MM-7400': 'com_sanyo7400',
              'MM-8300': 'com_sanyo8300',
              'PM-8200': 'com_sanyo8200',
              'RL-4920': 'com_sanyo4920',
              'RL-4930': 'com_sanyo4930',
              'SCP-4900': 'com_sanyo4900',
              'SCP-5300': 'com_sanyo5300',
              'SCP-5400': 'com_sanyo5400',
              'SCP-5500': 'com_sanyo5500',
              'SCP-7200': 'com_sanyo7200',
              'SCP-7300': 'com_sanyo7300',
              'SCP-8100': 'com_sanyo8100',
              'SCP-8100 (Bell Mobility)': 'com_sanyo8100_bell',
              'SCH-A310': 'com_samsungscha310',
              'SPH-A460': 'com_samsungspha460',
              'SPH-A620 (VGA1000)': 'com_samsungspha620',
              'SPH-A660 (VI660)': 'com_samsungspha660',
              'SPH-A740': 'com_samsungspha740',
              'SPH-A840': 'com_samsungspha840',
              'SPH-N200': 'com_samsungsphn200',
              'SPH-N400': 'com_samsungsphn400',
              'SCH-A650': 'com_samsungscha650',
              'SCH-A670': 'com_samsungscha670',
              'SK6100 (Pelephone)' : 'com_sk6100', 
              'VM4050 (Sprint)' : 'com_toshibavm4050',
              'VI-2300': 'com_sanyo2300',
              'LG-VI5225 (STI-Mobile)': 'com_lgvi5225',
              'Other CDMA phone': 'com_othercdma',
              }

if __debug__:
    phonemodels.update( {'Audiovox CDM-8900': 'com_audiovoxcdm8900',     # phone is too fragile for normal use
                         'SPH-A680': 'com_samsungspha680',
                         })

# update the module path
for k, e in phonemodels.items():
    phonemodels[k]=__name__+'.'+e

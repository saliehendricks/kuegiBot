# Combined results
## bybit
| | | | | | | | | | | | 
|---|---|---|---|---|---|---|---|---|---|---|
| 14mo |  pos: 325 | profit: 693.41 | HH: 693.41 | maxDD: 12.62 | maxExp: 668.36 | rel: 46.04 | UW days: 22.2 | pos days: 0.0/2.1/20.2 |

```
bot.add_strategy(KuegiStrategy(
    min_channel_size_factor=0, max_channel_size_factor=16,
    entry_tightening=1, bars_till_cancel_triggered=5,
    stop_entry=True, delayed_entry=True, delayed_cancel=True, cancel_on_filter= False)
                 .withChannel(max_look_back=13, threshold_factor=2.6, buffer_factor=0.05,max_dist_factor=2,max_swing_length=4)
                 .withRM(risk_factor=2, max_risk_mul=2, risk_type=1, atr_factor=2)
                 .withExitModule(SimpleBE(factor=0.5, buffer=-0.1))
                 .withExitModule(SimpleBE(factor=1, buffer=0.5))
                 .withExitModule(ParaTrail(accInit=0.015, accInc=0.015, accMax=0.03))
                 .withEntryFilter(DayOfWeekFilter(55))
                 )
                 
bot.add_strategy(SfpStrategy(
    init_stop_type=1, tp_fac=12,
    min_wick_fac=0.5, min_swing_length=11,
    range_length=70, min_rej_length= 35, range_filter_fac=0,
    close_on_opposite=False)
                 .withChannel(max_look_back=13, threshold_factor=0.8, buffer_factor=0.05, max_dist_factor=1,
                              max_swing_length=4)
                 .withRM(risk_factor=4, max_risk_mul=2, risk_type=0, atr_factor=1)
                 .withExitModule(SimpleBE(factor=0.6, buffer=0.4))
                 .withExitModule(SimpleBE(factor=1.6, buffer=0.8))
                 .withExitModule(ParaTrail(accInit=0.007, accInc=0.018, accMax=0.07))
                 .withEntryFilter(DayOfWeekFilter(61))
                 )
```

# single strat

## Kuegi

### bybit
good be levels kuegi: 5/-1 10/5 13/8 15/11

KuegiBot weekdays bybit rel / maxDD:
* Monday: 0.29 / 8
* Tuesday: 6.3 / 4.58
* Wednesday: 4.91 / 7.72
* Thursday: 4.72 / 6.86
* Friday: 6.87 / 6.76
* Saturday: 4.71 / 7.65
* Sunday: -1 / 9,6

(last run  with data from 2020-04-04)

| | | | | | | | | | | | 
|---|---|---|---|---|---|---|---|---|---|---|
14 mo | pos: 223 | profit: 192.45 | HH: 193.74 | maxDD: 6.49 | maxExp: 324.20 | rel: 24.85 | UW days: 23.5 | pos days: 0.0/2.5/19.3

```
    min_channel_size_factor=0, max_channel_size_factor=16,
    entry_tightening=1, bars_till_cancel_triggered=5,
    stop_entry=True, delayed_entry=True, delayed_cancel=True)
                 .withChannel(max_look_back=13, threshold_factor=2.6, buffer_factor=0.05,max_dist_factor=2,max_swing_length=4)
                 .withRM(risk_factor=1, max_risk_mul=2, risk_type=1, atr_factor=2)
                 .withExitModule(SimpleBE(factor=0.5, buffer=-0.1))
                 .withExitModule(SimpleBE(factor=1, buffer=0.5))
                 .withExitModule(ParaTrail(accInit=0.015, accInc=0.015, accMax=0.03))
                 .withEntryFilter(DayOfWeekFilter(55))
```
### bitmex

| | | | | | | | | | | | 
|---|---|---|---|---|---|---|---|---|---|---|
 48mo | pos: 999 | profit: 509.66 | HH: 512.20 | maxDD: 21.76 | maxExp: 651.65 | rel: 5.92 | UW days: 66.0 | pos days: 0.0/4.6/22.0
 24mo | pos: 471 | profit: 298.21 | HH: 300.75 | maxDD: 10.86 | maxExp: 387.49 | rel: 13.99 | UW days: 24.4 | pos days: 0.0/4.7/21.3
 12mo | pos: 236 | profit: 127.75 | HH: 130.28 | maxDD: 10.86 | maxExp: 220.27 | rel: 11.63 | UW days: 24.4 | pos days: 0.0/4.3/18.3

```
    min_channel_size_factor=1.618, max_channel_size_factor=16,
    entry_tightening=0.1, bars_till_cancel_triggered=3,
    stop_entry=True, delayed_entry=False, delayed_cancel=True,cancel_on_filter=True)
    .withChannel( max_look_back=13, threshold_factor=2.5, buffer_factor=-0.0618,max_dist_factor=1, max_swing_length=4)
    .withRM(risk_factor=1, max_risk_mul=2, risk_type=0)
    .withExitModule(SimpleBE(factor=1.2, buffer=0.2))
    .withExitModule(ParaTrail(accInit=0.004, accInc=0.003, accMax=0.07))
                 .withEntryFilter(DayOfWeekFilter(63))
    )
```

### binance

## SFP

### bybit

good be levels sfp: 6/4  10/5  16/8  20/16 -> 7.22


(last run  with data from 2020-04-04)

| | | | | | | | | | | | 
|---|---|---|---|---|---|---|---|---|---|---|
 14 month | pos: 118 | profit: 296.68 | HH: 296.68 | maxDD: 16.32 | maxExp: 549.48 | rel: 13.14 | UW days: 64.3 | pos days: 0.0/1.0/8.2
 
 ```
    init_stop_type=1, tp_fac=12,
    min_wick_fac=0.5, min_swing_length=11,
    range_length=70, min_rej_length= 35, range_filter_fac=0,
    close_on_opposite=False)
                 .withChannel(max_look_back=13, threshold_factor=0.8, buffer_factor=0.05, max_dist_factor=1,
                              max_swing_length=4)
                 .withRM(risk_factor=4, max_risk_mul=2, risk_type=0)
                 .withExitModule(SimpleBE(factor=0.6, buffer=0.4))
                 .withExitModule(SimpleBE(factor=1.6, buffer=0.8))
                 .withExitModule(ParaTrail(accInit=0.007, accInc=0.018, accMax=0.07))
                 .withEntryFilter(DayOfWeekFilter(63))
```

### bitmex

| | | | | | | | | | | | 
|---|---|---|---|---|---|---|---|---|---|---|
  24 mo |  pos: 604 | profit: 101.65 | HH: 117.14 | maxDD: 18.33 | rel: 2.83 | UW days: 113.1
 
 ```
             init_stop_type=2, tp_fac=25,
             min_wick_fac=0.3, min_swing_length=2,
             range_length=20, range_filter_fac=0,
             close_on_opposite=False)
    .withChannel(max_look_back=13, threshold_factor=0.8, buffer_factor=0.05,max_dist_factor=1,max_swing_length=4)
    .withRM(risk_factor=1, max_risk_mul=2, risk_type=0)
    .withExitModule(SimpleBE(factor=1, buffer=0.3))
    .withTrail(trail_to_swing=False, delayed_swing=False,trail_back=False)
```
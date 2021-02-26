import datetime

def get_current_time():
    now = datetime.datetime.now()
    year_strip_0x = hex(now.year)[2:]
    lsb_raw = year_strip_0x[1:]
    if (len(lsb_raw) <= 1):
        hex_year_a = "0" + lsb_raw
    else:
        hex_year_a = lsb_raw
    split_by_lsb_raw = year_strip_0x.split(lsb_raw)
    msb_raw = split_by_lsb_raw[0]
    if (len(msb_raw) <= 1):
        hex_year_b = "0" + msb_raw
    else:
        hex_year_b = msb_raw

    month_strip_0x = hex(now.month)[2:]
    if (len(month_strip_0x) <=1 ):
        hex_month = "0" + month_strip_0x
    else:
        hex_month = month_strip_0x

    day_strip_0x = hex(now.day)[2:]
    if (len(day_strip_0x) <= 1):
        hex_day = "0" + day_strip_0x
    else:
        hex_day = day_strip_0x

    hour_strip_0x = hex(now.hour)[2:]
    if (len(hour_strip_0x) <= 1):
        hex_hour = "0" + hour_strip_0x
    else:
        hex_hour = hour_strip_0x

    minute_strip_0x = hex(now.minute)[2:]
    if (len(minute_strip_0x) <= 1):
        hex_minute = "0" + minute_strip_0x
    else:
        hex_minute = minute_strip_0x

    second_strip_0x = hex(now.second)[2:]
    if (len(second_strip_0x) <= 1):
        hex_second = "0" + second_strip_0x
    else:
        hex_second = second_strip_0x

    weekday_strip_0x = hex(now.weekday() + 1)[2:]
    if (len(weekday_strip_0x) <= 1):
        hex_weekday = "0" + weekday_strip_0x
    else:
        hex_weekday = weekday_strip_0x

    hexasecond = hex(int((now.microsecond * 256) / 1000000))
    hexasecond_strip_0x = hexasecond[2:]
    if (len(hexasecond_strip_0x) <= 1):
        hex_fractions = "0" + hexasecond_strip_0x
    else:
        hex_fractions = hexasecond_strip_0x
    hex_answer = hex_year_a + " " + hex_year_b + " " + hex_month + " " + hex_day + " " + hex_hour + " " + hex_minute + " " + hex_second + " " + hex_weekday + " " + hex_fractions
    print(hex_answer)
    return bytearray.fromhex(hex_answer)

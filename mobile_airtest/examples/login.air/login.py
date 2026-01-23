# -*- encoding=utf8 -*-
__author__ = "admin"

from airtest.core.api import *

auto_setup(__file__)
touch(Template(r"tpl1763972756114.png", record_pos=(-0.117, -0.272), resolution=(900, 1600)))
if exists(Template(r"tpl1763973693047.png", record_pos=(-0.248, -0.327), resolution=(900, 1600))):
    touch(Template(r"tpl1763972881224.png", record_pos=(0.016, -0.339), resolution=(900, 1600)))
    touch(Template(r"tpl1763972897290.png", record_pos=(-0.017, -0.213), resolution=(900, 1600)))
    for i in range(10):
        keyevent("KEYCODE DEL")#清除输入框
else:
    touch(Template(r"tpl1763973441073.png", record_pos=(-0.109, -0.22), resolution=(900, 1600)))

text("格力测试啊啊")
sleep(1.0)
touch(Template(r"tpl1763973011858.png", record_pos=(-0.002, -0.033), resolution=(900, 1600)))
touch(Template(r"tpl1763973050649.png", record_pos=(-0.046, -0.111), resolution=(900, 1600)))
text("17751020356")
touch(Template(r"tpl1763973068108.png", record_pos=(-0.092, 0.136), resolution=(900, 1600)))
text("pms2025@!")
touch(Template(r"tpl1763973080558.png", record_pos=(-0.009, 0.397), resolution=(900, 1600)))

touch(Template(r"tpl1763973565127.png", record_pos=(0.242, 0.801), resolution=(900, 1600)))
touch(Template(r"tpl1763973572481.png", record_pos=(0.001, -0.223), resolution=(900, 1600)))






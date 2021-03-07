from machine import Pin, mem32
from rp2 import PIO, StateMachine, asm_pio
from array import array
from uctypes import addressof

fclock=125000000 #clock frequency
vsync_delay=520 #525 lines total, counting porches & blanking intervals

#DMA address constants
DMA_BASE=0x50000000
CH0_READ_ADDR  =DMA_BASE+0x000
CH0_WRITE_ADDR =DMA_BASE+0x004
CH0_TRANS_COUNT=DMA_BASE+0x008
CH0_CTRL_TRIG  =DMA_BASE+0x00c
CH0_AL1_CTRL   =DMA_BASE+0x010
CH1_READ_ADDR  =DMA_BASE+0x040
CH1_WRITE_ADDR =DMA_BASE+0x044
CH1_TRANS_COUNT=DMA_BASE+0x048
CH1_CTRL_TRIG  =DMA_BASE+0x04c
CH1_AL1_CTRL   =DMA_BASE+0x050

PIO0_BASE      =0x50200000
PIO0_TXF0      =PIO0_BASE+0x10
PIO0_SM0_CLKDIV=PIO0_BASE+0xc8

#vsync state machine
#ISR should be set to 3(?) less than desired line count
@asm_pio(set_init=PIO.OUT_HIGH)
def vsync():
    set(pins,1)
    mov(y,isr) #copy line count into y
    label("pulse")
    set(pins,0) #low pulse for two lines
    mov(x, y) #reset counter
    set(pins,1)
    label("countloop")
    jmp(x_dec, "countloop") #jump X != 0, post-decrement
    jmp("pulse")
    
vsync_sm = StateMachine(0, vsync, freq=31469, set_base=Pin(17))

vsync_sm.active(0)
vsync_sm.put(vsync_delay)
vsync_sm.exec("pull()")
vsync_sm.exec("mov(isr,osr)")
vsync_sm.active(1)

from machine import Pin, mem32
from rp2 import PIO, StateMachine, asm_pio
from array import array
from uctypes import addressof

fclock=125000000 #clock frequency
vsync_delay=488 #525 lines total, counting porches & blanking intervals
line_width=800 #640x480 has 800 columns
line_count=480
visible_line_width=640

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

USER_BANK_PAD_CONTROL_BASE = 0x4001c000
GPIO0_PAD_CONTROL = USER_BANK_PAD_CONTROL_BASE + 0x04
GPIO1_PAD_CONTROL = USER_BANK_PAD_CONTROL_BASE + 0x08
GPIO2_PAD_CONTROL = USER_BANK_PAD_CONTROL_BASE + 0x0C
GPIO3_PAD_CONTROL = USER_BANK_PAD_CONTROL_BASE + 0x10
GPIO4_PAD_CONTROL = USER_BANK_PAD_CONTROL_BASE + 0x14

#vsync state machine
#ISR should be set to 37 less than desired line count
@asm_pio(sideset_init=PIO.OUT_HIGH)
def vsync():
    label("pulse")
    mov(x, y)       .side(0) [1] #reset counter and start pulse
    nop()           .side(1) [7] #raise irq to signal hsync sm
    nop()                    [7]
    nop()                    [7]
    nop()                    [7]
    nop()
    irq(4)
    label("countloop")
    jmp(x_dec, "countloop")      #jump X != 0, post-decrement

#hsync state machine
#y stores total lines
#x stores current line 
@asm_pio(set_init=PIO.OUT_HIGH)
def hsync():
    mov(y,isr)
    label("frame_start")
    wait(1, irq, 4)                  #wait for vsync
    label("sync_pulse")
    set(pins,0)                 [5]
    set(pins,1)                 [2]
    irq(5)                      [31] #set interrupt after back porch
    nop()                       [5]
    irq(6)                      [1]
    jmp(x_dec, "sync_pulse")
    mov(x,y)                         #reset line counter
    jmp("frame_start")
    
# @asm_pio(out_init=(PIO.OUT_LOW, PIO.OUT_LOW, PIO.OUT_LOW, PIO.OUT_LOW, PIO.OUT_LOW, \
#                    PIO.OUT_LOW, PIO.OUT_LOW, PIO.OUT_LOW, PIO.OUT_LOW, PIO.OUT_LOW, \
#                    PIO.OUT_LOW, PIO.OUT_LOW, PIO.OUT_LOW, PIO.OUT_LOW, PIO.OUT_LOW, \
#                    PIO.OUT_LOW), out_shiftdir=PIO.SHIFT_RIGHT)
# def pixels():
#     mov(y,isr)
#     label("line_start")
#     wait(1, irq, 5)
#     label("pixel_start")
#     pull(noblock)             [1]
#     out(pins,16)
#     jmp(x_dec, "pixel_start")     #jump if we're not done with this line
#     mov(x, osr)                    #we know X is zero now
#     pull()
#     out(pins,16)                   #cheep way to write zero to pins during blanking interval

@asm_pio(set_init=(PIO.OUT_LOW, PIO.OUT_LOW, PIO.OUT_LOW, PIO.OUT_LOW, PIO.OUT_LOW))
def pixels():
    wait(1,irq,5)
    set(pins,31) [31]
    wait(1,irq,6)
    set(pins,0)

vsync_sm = StateMachine(0, vsync, freq=31469, sideset_base=Pin(17)) #run at line freq
hsync_sm = StateMachine(1, hsync, freq=1573438, set_base=Pin(16)) #run at 1/16 pixel clock
pixels_sm = StateMachine(2, pixels, freq=25175000, set_base=Pin(0)) #run at pixel clock

vsync_sm.active(0)
vsync_sm.put(vsync_delay)
vsync_sm.exec("pull()")
vsync_sm.exec("mov(y,osr)")
vsync_sm.active(1)

hsync_sm.active(0)
hsync_sm.put(line_count)
hsync_sm.exec("pull()")
hsync_sm.exec("mov(isr,osr)")
hsync_sm.active(1)

# pixels_sm.active(0)
# pixels_sm.put(visible_line_width)
# pixels_sm.exec("pull()")
# pixels_sm.exec("mov(y,osr)")
pixels_sm.active(1)

mem32[GPIO0_PAD_CONTROL] = mem32[GPIO0_PAD_CONTROL] | 0x31 #12ma drive current, fast slew rate
mem32[GPIO1_PAD_CONTROL] = mem32[GPIO1_PAD_CONTROL] | 0x31
mem32[GPIO2_PAD_CONTROL] = mem32[GPIO2_PAD_CONTROL] | 0x31
mem32[GPIO3_PAD_CONTROL] = mem32[GPIO3_PAD_CONTROL] | 0x31
mem32[GPIO4_PAD_CONTROL] = mem32[GPIO4_PAD_CONTROL] | 0x31


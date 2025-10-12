from machine import Pin, Timer

led = Pin(4, Pin.OUT)
reed = Pin(5, Pin.IN, Pin.PULL_UP)

debounce_timer = Timer(0)
debouncing = False


def debounce_callback(t: Timer):
    global debouncing
    debouncing = False


def reed_irq_handler(pin: Pin):
    global debouncing
    if not debouncing:
        debouncing = True
        debounce_timer.init(
            mode=Timer.ONE_SHOT, period=50,
            callback=debounce_callback
        )
        led.value(not led.value())
        print("beep")


reed.irq(trigger=Pin.IRQ_FALLING, handler=reed_irq_handler)

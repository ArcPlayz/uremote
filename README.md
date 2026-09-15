# uremote

This simple tool allows you to control your Linux desktop using your phone's browser.

## Usage

Install dependencies (evdev, aiohttp), run main.py, open served page on your phone.

You may need to add an udev rule (for example to ```/etc/udev/rules.d/50-uinput.rules```) to be able to access the uinput module:

```
KERNEL=="uinput", GROUP="input", MODE="0660"
```

Reload the rules:

```
sudo udevadm control --reload-rules && sudo udevadm trigger
```

You have to add yourself to the "input" group if you are not in it already (session restart required):

```
sudo usermod -aG input $USER
```

## This app may be buggy (especially with unstable connections)
In case of some locked buttons or touchpad just reload the page.

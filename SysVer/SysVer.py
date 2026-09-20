import platform
import os
import sys
import argparse
import json
import socket
import shutil
import datetime
import time
import subprocess

# Optional dependencies
try:
    import psutil
except Exception:
    psutil = None

try:
    from colorama import init as _color_init, Fore, Style
    _color_init(autoreset=True)
    COLOR_AVAILABLE = True
except Exception:
    COLOR_AVAILABLE = False
    class Fore:
        CYAN = ''
        YELLOW = ''
        GREEN = ''
        RED = ''
        RESET = ''
    class Style:
        RESET_ALL = ''

def safe_getlogin():
    try:
        return os.getlogin()
    except Exception:
        return os.environ.get('USER') or os.environ.get('USERNAME') or "Unknown"

def get_user_full_name():
    """Return a display name for the current user.

    On Windows tries to obtain the account Full Name (display name) via wmic/net/powershell.
    Falls back to POSIX gecos field or safe_getlogin().
    Returns either "Full Name (username)" when both available or a single name string.
    """
    username = os.environ.get('USERNAME') or os.environ.get('USER')
    # Windows-specific probes
    if os.name == 'nt' and username:
        # 1) wmic
        try:
            out = subprocess.check_output(['wmic', 'useraccount', 'where', f"name='{username}'", 'get', 'FullName'], stderr=subprocess.DEVNULL, universal_newlines=True)
            lines = [l.strip() for l in out.splitlines() if l.strip() and 'FullName' not in l]
            if lines:
                full = lines[0]
                if full and full != username:
                    return f"{full} ({username})"
                if full:
                    return full
        except Exception:
            pass

        # 2) net user
        try:
            out = subprocess.check_output(['net', 'user', username], stderr=subprocess.DEVNULL, universal_newlines=True)
            for line in out.splitlines():
                if 'Full Name' in line:
                    parts = line.split('Full Name', 1)[1].strip()
                    full = parts
                    if full and full != username:
                        return f"{full} ({username})"
                    if full:
                        return full
        except Exception:
            pass

        # 3) PowerShell Get-LocalUser
        try:
            out = subprocess.check_output(['powershell', '-NoProfile', '-Command', f"(Get-LocalUser -Name '{username}').FullName"], stderr=subprocess.DEVNULL, universal_newlines=True)
            out = out.strip()
            if out:
                if out != username:
                    return f"{out} ({username})"
                return out
        except Exception:
            pass

    # POSIX: try gecos
    try:
        import pwd
        pw = pwd.getpwuid(os.getuid())
        gecos = pw.pw_gecos.split(',')[0]
        if gecos:
            if username and gecos != username:
                return f"{gecos} ({username})"
            return gecos
    except Exception:
        pass

    # Fallback to safe login name
    return safe_getlogin()

def format_bytes(n):
    if n is None:
        return "Unknown"
    n = float(n)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if n < 1024:
            return f"{n:0.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"

def format_timedelta(seconds):
    if seconds is None:
        return "Unknown"
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hrs, seconds = divmod(seconds, 3600)
    mins, secs = divmod(seconds, 60)
    parts = []
    if days: parts.append(f"{days}d")
    if hrs: parts.append(f"{hrs}h")
    if mins: parts.append(f"{mins}m")
    parts.append(f"{secs}s")
    return " ".join(parts)

def get_ip_addresses():
    ips = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            addr = info[4][0]
            if addr.startswith("127.") or addr == "::1":
                continue
            ips.add(addr)
    except Exception:
        pass
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ips.add(s.getsockname()[0])
            s.close()
        except Exception:
            pass
    return sorted(ips) if ips else ["Unknown"]

def get_uptime():
    if psutil:
        try:
            return time.time() - psutil.boot_time()
        except Exception:
            return None
    if os.path.exists('/proc/uptime'):
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                return uptime_seconds
        except Exception:
            pass
    if os.name == 'nt':
        try:
            out = subprocess.check_output(['wmic', 'os', 'get', 'LastBootUpTime'], stderr=subprocess.DEVNULL, universal_newlines=True)
            lines = [l.strip() for l in out.splitlines() if l.strip() and 'LastBootUpTime' not in l]
            if lines:
                ts = lines[0]
                dt = datetime.datetime.strptime(ts[:14], "%Y%m%d%H%M%S")
                return (datetime.datetime.now() - dt).total_seconds()
        except Exception:
            pass
    return None

def get_disk_info():
    root = '/' if os.name != 'nt' else os.environ.get('SystemDrive', 'C:') + '\\'
    try:
        usage = shutil.disk_usage(root)
        return {
            'total': usage.total,
            'used': usage.used,
            'free': usage.free,
            'mount': root
        }
    except Exception:
        return {'total': None, 'used': None, 'free': None, 'mount': root}

def get_memory_info():
    if psutil:
        try:
            vm = psutil.virtual_memory()
            return {'total': vm.total, 'available': vm.available, 'used': vm.used, 'percent': vm.percent}
        except Exception:
            pass
    return {'total': None, 'available': None, 'used': None, 'percent': None}

def get_cpu_info():
    try:
        physical = psutil.cpu_count(logical=False) if psutil else None
        logical = psutil.cpu_count(logical=True) if psutil else os.cpu_count()
    except Exception:
        physical = None
        logical = os.cpu_count()
    freq = None
    if psutil:
        try:
            f = psutil.cpu_freq()
            freq = f.current if f else None
        except Exception:
            freq = None
    load = None
    if hasattr(os, "getloadavg"):
        try:
            load = os.getloadavg()
        except Exception:
            load = None
    return {'physical': physical, 'logical': logical, 'freq_mhz': freq, 'load_avg': load}

def get_processor_model():
    """Return a user-friendly processor model name if available.

    Tries cpuinfo package, then platform-specific probes (Linux /proc, macOS sysctl, Windows wmic),
    and falls back to platform.processor() or 'Unknown'.
    """
    # Try python-cpuinfo if installed
    try:
        import cpuinfo
        info = cpuinfo.get_cpu_info()
        brand = info.get('brand_raw') or info.get('brand')
        if brand:
            return brand.strip()
    except Exception:
        pass

    # Linux: /proc/cpuinfo
    try:
        if os.name != 'nt' and os.path.exists('/proc/cpuinfo'):
            with open('/proc/cpuinfo', 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.lower().startswith('model name') or line.lower().startswith('processor'):
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            val = parts[1].strip()
                            if val:
                                return val
    except Exception:
        pass

    # macOS: sysctl
    try:
        if sys.platform == 'darwin':
            out = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string'], stderr=subprocess.DEVNULL, universal_newlines=True)
            out = out.strip()
            if out:
                return out
    except Exception:
        pass

    # Windows: wmic
    try:
        if os.name == 'nt':
            out = subprocess.check_output(['wmic', 'cpu', 'get', 'Name'], stderr=subprocess.DEVNULL, universal_newlines=True)
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            # first line is header 'Name'
            if len(lines) >= 2:
                return lines[1]
    except Exception:
        pass

    # Fallbacks
    try:
        p = platform.processor()
        if p:
            return p
    except Exception:
        pass

    try:
        # uname().processor may have useful info on some systems
        p2 = platform.uname().processor
        if p2:
            return p2
    except Exception:
        pass

    return 'Unknown'

def get_sys_info():
    uname = platform.uname()
    os_name = f"{platform.system()} {platform.release()}"
    kernel = (platform.version().split()[0] if platform.version() else "Unknown")
    arch = platform.machine() or "Unknown"
    processor = get_processor_model() or "Unknown"
    python_version = platform.python_version()
    user = get_user_full_name()
    hostname = socket.gethostname()
    ips = get_ip_addresses()
    uptime = get_uptime()
    boot = None
    if uptime is not None:
        boot = datetime.datetime.now() - datetime.timedelta(seconds=int(uptime))
        boot = boot.isoformat(sep=' ', timespec='seconds')
    disk = get_disk_info()
    mem = get_memory_info()
    cpu = get_cpu_info()
    info = {
        "Operating system": f"Windows 11" if platform.system() == "Windows" and int(platform.version().split('.')[2]) >= 22000 else f"{platform.system()} {platform.release()}",
        "Kernel version": kernel,
        "Architecture": arch,
        "Processor type": processor,
        "Python version": python_version,
        "User": user,
        "Hostname": hostname,
        "IP addresses": ', '.join(ips),
        "Uptime": format_timedelta(uptime),
        "Boot time": boot or "Unknown",
        "CPU (physical/logical)": f"{cpu['physical'] or '?'} / {cpu['logical'] or '?'}",
        "CPU frequency (MHz)": f"{cpu['freq_mhz']:.1f}" if cpu['freq_mhz'] else "Unknown",
        "Load average (1m,5m,15m)": ', '.join(f"{x:.2f}" for x in cpu['load_avg']) if cpu['load_avg'] else "Unknown",
        "Memory (total/available/used)": f"{format_bytes(mem['total'])} / {format_bytes(mem['available'])} / {format_bytes(mem['used'])}",
        "Disk": f"{format_bytes(disk['total'])} total, {format_bytes(disk['free'])} free ({disk['mount']})"
    }
    return info

def render_box(info, use_color=True):
    items = list(info.items())
    rows = [f"{k}: {v}" for k, v in items]
    max_len = max(len(r) for r in rows)
    pad = 4
    width = max_len + pad
    sep = '+' + '-' * (width - 2) + '+'
    lines = [sep]
    for k, v in items:
        text = f"{k}: {v}"
        if use_color and COLOR_AVAILABLE:
            label = Fore.CYAN + k + Fore.RESET
            row_text = f"{label}: {v}"
            raw = f"{k}: {v}"
            padded = raw.ljust(width - 4)
            colored = row_text.replace(f"{k}:", Fore.CYAN + k + Fore.RESET + ":")
            colored_padded = colored.split(":", 1)[0] + ":" + padded[len(f"{k}:"):]
            lines.append(f"| {colored_padded} |")
        else:
            lines.append(f"| {text.ljust(width - 4)} |")
    lines.append(sep)
    return "\n".join(lines)

def render_table(info, use_color=True):
    items = list(info.items())
    key_w = max(len(k) for k, _ in items)
    val_w = max(len(v) for _, v in items)
    sep = f"+-{'-'*key_w}-+-{'-'*val_w}-+"
    lines = [sep]
    for k, v in items:
        if use_color and COLOR_AVAILABLE:
            k_display = Fore.CYAN + k.ljust(key_w) + Fore.RESET
        else:
            k_display = k.ljust(key_w)
        lines.append(f"| {k_display} | {str(v).ljust(val_w)} |")
    lines.append(sep)
    return "\n".join(lines)

def main(argv=None):
    parser = argparse.ArgumentParser(description="Advanced system information utility")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--format", choices=['box', 'table'], default='box', help="Output format")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    parser.add_argument("--verbose", action="store_true", help="Show additional debug info (if any)")
    args = parser.parse_args(argv)

    info = get_sys_info()
    use_color = not args.no_color

    if args.json:
        print(json.dumps(info, indent=2))
        return

    if args.format == 'box':
        out = render_box(info, use_color=use_color)
    else:
        out = render_table(info, use_color=use_color)

    try:
        os.system('cls' if os.name == 'nt' else 'clear')
    except Exception:
        pass

    print(out)

if __name__ == "__main__":
    main()


from datetime import datetime
from ipaddress import IPv4Address , IPv4Network

from ..constants import SOC_ITEM
from .base import GameState, Room

class SOCRoom(Room):
    def __init__(self, data_path):
        super().__init__(
            "soc",
            "You enter the SOC Triage Desk.\n"
            "A cluttered screen shows failed SSH login attempts.\n"
            f"Items here: {SOC_ITEM}",
        )
        self.data_path = data_path
    
    def inspect(self, state: GameState, item: str) -> list[str]:
        if item != SOC_ITEM:
           return super().inspect(item)

        try:
            keypad, max_subnet, max_count, sample, malform_count = ( self.read_auth_log(f"{self.data_path}/{SOC_ITEM}"))
        except (OSError, ValueError) as error:
            return [f"[Room SOC] Could not analyze {SOC_ITEM}: {error}"]

        state.tokens["KEYPAD"] = keypad
        state.inventory.add("KEYPAD")
        return [ "[Room SOC] Parsing logs...",
        f"TOKEN[KEYPAD]={keypad}",
        f"EVIDENCE[KEYPAD].TOP24={max_subnet}",
        f"EVIDENCE[KEYPAD].COUNT={max_count}",
        f"EVIDENCE[KEYPAD].SAMPLE={sample}",
        f"EVIDENCE[KEYPAD].MALFORMED_SKIPPED={malform_count}",]

    def read_auth_log(self, path):
        malform_count = 0
        fail_ips = []
        fail_record = []
        subnet_count = {}
        ip_count = {}
        with open(path, "r", encoding="utf-8") as file:
            for line in file:
                part = line.strip().split()
                if not self.check_valid_log_entry(part):
                    malform_count += 1
                    continue  
                if part[3] == "Failed":
                    fail_ips.append(part[8])
                    fail_record.append((part[8], line.strip()))  # Add the source IP and log line to failed_record
                    subnet = self.get_subnet(part[8])
                    subnet_count[subnet] = subnet_count.get(subnet, 0) + 1

            #print("Malformed Count:", malform_count)
            
            #print("subnet_count:", subnet_count)
            max_subnet = max(subnet_count, key=subnet_count.get)
            if not subnet_count:
                raise ValueError("No valid failed-login records found.")
            max_count = subnet_count[max_subnet]

            #print("Winning subnet:", max_subnet)
            #print("Failed attempts:", max_count)

            for ip in fail_ips:
                if self.get_subnet(ip) == max_subnet:
                    ip_count[ip] = ip_count.get(ip, 0) + 1
            max_ip = max(ip_count, key=ip_count.get)
            #print("IP Count:", max_ip, "with", ip_count[max_ip], "failed attempts")

            for ip, line in fail_record:
                if self.get_subnet(ip) == max_subnet:
                    sample = line
                    break

            Octet = max_ip.split(".")
            last_octet=Octet[-1]
            keypad = last_octet + str(max_count)
            return (keypad, max_subnet, max_count, sample, malform_count)

    def check_valid_log_entry(self, part):
        if (len(part) == 13 and self.check_timestamp(part[0]) and part[2].startswith("sshd[") and part[2].endswith("]:") and part[3] in ("Accepted", "Failed") 
            and part[4] == "password" and part[5] == "for" and part[7] == "from" and self.check_ipv4(part[8]) and part[9] == "port" and part[11] == "protocol" 
            and part[12] == "2"):
            try:
                pid_txt = part[2][5:-2]
                int(pid_txt)  # Check if pid is an integer
                int(part[10]) # Check if port is an integer
            except ValueError:    
                return False
            return True
        return False

    def check_timestamp(self, timestamp):
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False

    def check_ipv4(self, address):
        try:
            IPv4Address(address)
            return True
        except ValueError:
            return False
    def get_subnet(self, ip):
        network = IPv4Network(f"{ip}/24", strict=False)
        return str(network)

if __name__ == "__main__":
    room = SOCRoom("data")
    result = room.read_auth_log("data/auth.log")
    print(result)

    
    
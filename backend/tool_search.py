"""Keyword-based tool search for the progressive-disclosure mode.

The search pipeline works as follows:

1.  **Tokenise** the user query and each tool's combined text (name +
    description + parameters) into lowercase alphanumeric tokens.
2.  **Expand** query tokens using :data:`KEYWORD_MAP` — a German→English
    synonym dictionary that bridges language gaps (e.g. ``"wetter"`` →
    ``"weather"``).
3.  **Match** each expanded query token against every tool's token set and
    accumulate a score per tool (one point per matching token).
4.  **Rank** tools by descending score and return the top *k* results.

This module is deliberately dependency-free (uses only :mod:`re`) so it can
be used in both the backend and standalone MCP server contexts.
"""

import re


#: German→English keyword mapping for cross-language tool search.
#:
#: Keys are German terms (lowercase); values are lists of English equivalents
#: that should also be searched.  This allows a German user query like
#: "Wie ist das *Wetter* in Leipzig?" to match English tool names and
#: descriptions such as ``get_weather``.
#:
#: Note: some keys appear multiple times in the literal dict below; in Python
#: the last definition wins.  This is a known data-quality issue but does not
#: affect runtime behaviour because the matching logic is token-based.
KEYWORD_MAP: dict[str, list[str]] = {
    "wetter": ["weather"],
    "kunde": ["customer"],
    "kunden": ["customer"],
    "bestellung": ["order"],
    "bestellungen": ["order"],
    "rechnung": ["invoice"],
    "finanzen": ["finance"],
    "finanziell": ["finance"],
    "temperatur": ["temperature"],
    "luftfeuchtigkeit": ["humidity"],
    "wind": ["wind"],
    "regen": ["precipitation", "rain"],
    "uv": ["uv"],
    "auftrag": ["order"],
    "support": ["support"],
    "ticket": ["ticket"],
    "steuer": ["tax"],
    "budget": ["budget"],
    "datenbank": ["database"],
    "server": ["server"],
    "cache": ["cache"],
    "log": ["log"],
    "backup": ["backup"],
    "datei": ["file"],
    "suche": ["search"],
    "bericht": ["report"],
    "analyse": ["analyze"],
    "erstellen": ["create"],
    "löschen": ["delete"],
    "aktualisieren": ["update"],
    "abrechnung": ["invoice"],
    "lieferung": ["deliver", "ship"],
    "stornieren": ["cancel"],
    " prognose": ["forecast"],
    "warnung": ["alert"],
    "qualität": ["quality"],
    "index": ["index"],
    "konfiguration": ["config"],
    "speicher": ["storage"],
    "warteschlange": ["queue"],
    "speicherplatz": ["storage"],
    "dokument": ["document"],
    "team": ["team"],
    "benachrichtigung": ["notify"],
    "webhook": ["webhook"],
    "verschlüsseln": ["encrypt"],
    "entschlüsseln": ["decrypt"],
    "importieren": ["import"],
    "exportieren": ["export"],
    "metriken": ["metrics"],
    "alarm": ["alert"],
    "warnungen": ["alert"],
    "zahlung": ["payment"],
    "schließen": ["close"],
    "öffnen": ["open"],
    "starten": ["start"],
    "stoppen": ["stop"],
    "neustarten": ["restart"],
    "anhalten": ["pause"],
    "fortsetzen": ["resume"],
    "überwachen": ["monitor"],
    "prüfen": ["check"],
    "validieren": ["validate"],
    "synchronisieren": ["sync"],
    "bereitstellen": ["deploy"],
    "optimieren": ["optimize"],
    "komprimieren": ["compress"],
    "bereinigen": ["clean"],
    "rotieren": ["rotate"],
    "verschmelzen": ["merge"],
    "kommunikation": ["communication"],
    "historie": ["history"],
    "statistiken": ["statistics"],
    "bilanz": ["balance"],
    "einkommen": ["income"],
    "ausgaben": ["expenses"],
    "cashflow": ["cash_flow"],
    "produktpalette": ["inventory"],
    "datei": ["file"],
    "dateien": ["file"],
    "verzeichnis": ["directory"],
    "archive": ["archive"],
    "skript": ["script"],
    "migration": ["migration"],
    "vulnerability": ["vulnerability"],
    "sicherheit": ["security"],
    "leistung": ["performance"],
    "netzwerk": ["network"],
    "ip": ["ip"],
    "dns": ["dns"],
    "fehler": ["error"],
    "ausnahme": ["exception"],
    "debug": ["debug"],
    "protokoll": ["protocol"],
    "ereignis": ["event"],
    "nachricht": ["message"],
    "task": ["task"],
    "job": ["job"],
    "cron": ["cron"],
    "schedule": ["schedule"],
    "timer": ["timer"],
    "worker": ["worker"],
    "prozess": ["process"],
    "umgebung": ["environment"],
    "variablen": ["variables"],
    "geheimnis": ["secret"],
    "schlüssel": ["key"],
    "token": ["token"],
    "zertifikat": ["certificate"],
    "ssl": ["ssl"],
    "tls": ["tls"],
    "oauth": ["oauth"],
    "bearer": ["bearer"],
    "auth": ["auth"],
    "login": ["login"],
    "logout": ["logout"],
    "register": ["register"],
    "password": ["password"],
    "user": ["user"],
    "admin": ["admin"],
    "role": ["role"],
    "permission": ["permission"],
    "access": ["access"],
    "denied": ["denied"],
    "forbidden": ["forbidden"],
    "unauthorized": ["unauthorized"],
    "notfound": ["not_found"],
    "timeout": ["timeout"],
    "retry": ["retry"],
    "rate_limit": ["rate_limit"],
    "quota": ["quota"],
    "billing": ["billing"],
    "subscription": ["subscription"],
    "plan": ["plan"],
    "tier": ["tier"],
    "upgrade": ["upgrade"],
    "downgrade": ["downgrade"],
    "cancel": ["cancel"],
    "renew": ["renew"],
    "expire": ["expire"],
    "revoke": ["revoke"],
    "issue": ["issue"],
    "verify": ["verify"],
    "sign": ["sign"],
    "hash": ["hash"],
    "salt": ["salt"],
    "pepper": ["pepper"],
    "cipher": ["cipher"],
    "aes": ["aes"],
    "rsa": ["rsa"],
    "ecdsa": ["ecdsa"],
    "hmac": ["hmac"],
    "jwt": ["jwt"],
    "jws": ["jws"],
    "jwe": ["jwe"],
    "jwk": ["jwk"],
    "pem": ["pem"],
    "der": ["der"],
    "p12": ["p12"],
    "pfx": ["pfx"],
    "keystore": ["keystore"],
    "truststore": ["truststore"],
    "keytab": ["keytab"],
    "krb5": ["krb5"],
    "spnego": ["spnego"],
    "saml": ["saml"],
    "oidc": ["oidc"],
    "openid": ["openid"],
    "sso": ["sso"],
    "mfa": ["mfa"],
    "2fa": ["2fa"],
    "totp": ["totp"],
    "hotp": ["hotp"],
    "u2f": ["u2f"],
    "fido": ["fido"],
    "webauthn": ["webauthn"],
    "ctap": ["ctap"],
    "nfc": ["nfc"],
    "ble": ["ble"],
    "usb": ["usb"],
    "hid": ["hid"],
    "scard": ["scard"],
    "pcsc": ["pcsc"],
    "pkcs11": ["pkcs11"],
    "pkcs12": ["pkcs12"],
    "x509": ["x509"],
    "asn1": ["asn1"],
    "ocsp": ["ocsp"],
    "cps": ["cps"],
    "cp": ["cp"],
    "cpl": ["cpl"],
    "cpp": ["cpp"],
    "cpx": ["cpx"],
    "cpu": ["cpu"],
    "gpu": ["gpu"],
    "tpu": ["tpu"],
    "fpga": ["fpga"],
    "asic": ["asic"],
    "soc": ["soc"],
    "ram": ["ram"],
    "rom": ["rom"],
    "flash": ["flash"],
    "eeprom": ["eeprom"],
    "sd": ["sd"],
    "ssd": ["ssd"],
    "hdd": ["hdd"],
    "nvme": ["nvme"],
    "sata": ["sata"],
    "sas": ["sas"],
    "scsi": ["scsi"],
    "ide": ["ide"],
    "ahci": ["ahci"],
    "raid": ["raid"],
    "lvm": ["lvm"],
    "zfs": ["zfs"],
    "btrfs": ["btrfs"],
    "ext4": ["ext4"],
    "xfs": ["xfs"],
    "ntfs": ["ntfs"],
    "fat": ["fat"],
    "exfat": ["exfat"],
    "hfs": ["hfs"],
    "apfs": ["apfs"],
    "iso": ["iso"],
    "img": ["img"],
    "vmdk": ["vmdk"],
    "vhd": ["vhd"],
    "vhdx": ["vhdx"],
    "qcow2": ["qcow2"],
    "ova": ["ova"],
    "ovf": ["ovf"],
    "vagrant": ["vagrant"],
    "docker": ["docker"],
    "podman": ["podman"],
    "kubernetes": ["kubernetes"],
    "k8s": ["k8s"],
    "helm": ["helm"],
    "kubectl": ["kubectl"],
    "oc": ["oc"],
    "openshift": ["openshift"],
    "okd": ["okd"],
    "k3s": ["k3s"],
    "k3os": ["k3os"],
    "rke": ["rke"],
    "rke2": ["rke2"],
    "rancher": ["rancher"],
    "dockerfile": ["dockerfile"],
    "compose": ["compose"],
    "swarm": ["swarm"],
    "nomad": ["nomad"],
    "consul": ["consul"],
    "vault": ["vault"],
    "terraform": ["terraform"],
    "ansible": ["ansible"],
    "puppet": ["puppet"],
    "chef": ["chef"],
    "saltstack": ["saltstack"],
    "packer": ["packer"],
    "vagrant": ["vagrant"],
    "cloud": ["cloud"],
    "aws": ["aws"],
    "gcp": ["gcp"],
    "azure": ["azure"],
    "digitalocean": ["digitalocean"],
    "linode": ["linode"],
    "vultr": ["vultr"],
    "hetzner": ["hetzner"],
    "ovh": ["ovh"],
    "scaleway": ["scaleway"],
    "do": ["do"],
    "lo": ["lo"],
    "eth": ["eth"],
    "wlan": ["wlan"],
    "wwan": ["wwan"],
    "vpn": ["vpn"],
    "tor": ["tor"],
    "i2p": ["i2p"],
    "proxy": ["proxy"],
    "socks": ["socks"],
    "http": ["http"],
    "https": ["https"],
    "ftp": ["ftp"],
    "sftp": ["sftp"],
    "scp": ["scp"],
    "rsync": ["rsync"],
    "ssh": ["ssh"],
    "telnet": ["telnet"],
    "smtp": ["smtp"],
    "imap": ["imap"],
    "pop3": ["pop3"],
    "sieve": ["sieve"],
    "ldap": ["ldap"],
    "ldaps": ["ldaps"],
    "kerberos": ["kerberos"],
    "gssapi": ["gssapi"],
    "spnego": ["spnego"],
    "dns": ["dns"],
    "dhcp": ["dhcp"],
    "tftp": ["tftp"],
    "nfs": ["nfs"],
    "cifs": ["cifs"],
    "smb": ["smb"],
    "afp": ["afp"],
    "ncp": ["ncp"],
    "sshfs": ["sshfs"],
    "webdav": ["webdav"],
    "dav": ["dav"],
    "carddav": ["carddav"],
    "caldav": ["caldav"],
    "groupware": ["groupware"],
    "exchange": ["exchange"],
    "ews": ["ews"],
    "imap": ["imap"],
    "pop3": ["pop3"],
    "smtp": ["smtp"],
    "smtps": ["smtps"],
    "submission": ["submission"],
    "imap": ["imap"],
    "imaps": ["imaps"],
    "pop3": ["pop3"],
    "pop3s": ["pop3s"],
    "sieve": ["sieve"],
    "managesieve": ["managesieve"],
    "ldap": ["ldap"],
    "ldaps": ["ldaps"],
    "kerberos": ["kerberos"],
    "gssapi": ["gssapi"],
    "spnego": ["spnego"],
    "dns": ["dns"],
    "dhcp": ["dhcp"],
    "tftp": ["tftp"],
    "nfs": ["nfs"],
    "cifs": ["cifs"],
    "smb": ["smb"],
    "afp": ["afp"],
    "ncp": ["ncp"],
    "sshfs": ["sshfs"],
    "webdav": ["webdav"],
    "dav": ["dav"],
    "carddav": ["carddav"],
    "caldav": ["caldav"],
    "groupware": ["groupware"],
    "exchange": ["exchange"],
    "ews": ["ews"],
}


def _tokenize(text: str) -> list[str]:
    """Split *text* into lowercase alphanumeric tokens (including umlauts)."""
    return re.findall(r"[a-zäöüß0-9]+", text.lower())


def _expand_tokens(tokens: list[str]) -> list[str]:
    """Expand German tokens to their English equivalents via :data:`KEYWORD_MAP`.

    Tokens that have no mapping are kept as-is, so the result always contains
    at least the original tokens.
    """
    expanded = list(tokens)
    for token in tokens:
        if token in KEYWORD_MAP:
            expanded.extend(KEYWORD_MAP[token])
    return expanded


def build_index(tools: list[dict]) -> dict[str, list[str]]:
    """Build an inverted index mapping tokens → list of tool names.

    Args:
        tools: List of tool dicts with ``name``, ``description``, and
            ``parameters`` keys.

    Returns:
        A dict where each key is a lowercase token and each value is a list of
        tool names that contain that token in their name, description, or
        parameter text.
    """
    index: dict[str, list[str]] = {}
    for tool in tools:
        name = tool.get("name", "")
        desc = tool.get("description", "")
        params = tool.get("parameters", {})
        param_text = " ".join(
            str(v) for v in params.get("properties", {}).values()
        )
        combined = f"{name} {desc} {param_text}"
        tokens = _tokenize(combined)
        for token in set(tokens):
            index.setdefault(token, []).append(name)
    return index


def search(
    query: str,
    tools: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """Search the tool list for tools relevant to *query*.

    The query is tokenised and expanded (German→English) before matching
    against each tool's combined text.  Tools are ranked by the number of
    matching tokens (descending).

    Args:
        query: The user's search query (may be German or English).
        tools: The full list of tool dicts to search within.
        top_k: Maximum number of results to return (default 5).

    Returns:
        A list of up to *top_k* tool dicts, ranked by relevance.
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    query_tokens = _expand_tokens(query_tokens)

    tool_map = {t["name"]: t for t in tools}
    scores: dict[str, float] = {}

    for qt in query_tokens:
        for tool_name in _get_matching_tools(qt, tools):
            scores[tool_name] = scores.get(tool_name, 0) + 1

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [tool_map[name] for name, _ in ranked[:top_k]]


def _get_matching_tools(query_token: str, tools: list[dict]) -> list[str]:
    """Return names of tools whose name or description contains *query_token*.

    Args:
        query_token: A single lowercase token to search for.
        tools: The full list of tool dicts to search within.

    Returns:
        A list of tool names that match the query token.
    """
    matches = []
    for tool in tools:
        name = tool.get("name", "").lower()
        desc = tool.get("description", "").lower()
        if query_token in name or query_token in desc:
            matches.append(tool["name"])
    return matches

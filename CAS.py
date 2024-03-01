from requests import Session
from re import search
from code_recognize import recognizeBytes


class CasClient:
    """Class representing a CAS client. Example usage:

    ```python
    client = CasClient("<Your username>", "<Your password>") # Instantiate a CAS client
    assert client.login() # Login to CAS
    assert client.service("https://jw.ustc.edu.cn/ucas-sso/login") # Login to services that use the CAS system
    x = client.session # Use the session object to issue requests
    r = x.get("https://jw.ustc.edu.cn/***")
    assert "<Expected content>" in r.text
    ```
    """

    def __init__(
        self, username: str, password: str, header: dict = {}, debug: bool = False
    ) -> None:
        """Initialize a CAS client.

        :param username: Your username.
        :param password: Your password.
        :param header: A dict of additional headers to be added to the session object.
        :param debug: If set to True, the client will not verify the SSL certificate of the CAS server. This is useful when you try to monitor the network traffic issued by this lib using a proxy like Fiddler.
        :param verification: Verification code processing function. Takes binary as input and returns the verification code as a string. If not provided, the client will try to bypass verification code.
        """
        self.username = username
        self.password = password
        self.session = Session()
        self.session.headers.update(header)
        self.debug = debug

    def login(self) -> bool:
        """Login to CAS. Return True if login succeeds, False otherwise."""
        url = "https://passport.ustc.edu.cn/login"
        r = self.session.get(url, verify=(not self.debug))
        if r.url == "https://passport.ustc.edu.cn/success.jsp":
            return True  # Already logged in
        s = search(r'\$\("#CAS_LT"\).val\("(.*)"\);', r.text)
        cas_lt = s.group(1)
        need_verification = (
            "var showCode = '1';" in r.text
        )  # Auto-detect if verification code is required
        form_data = {
            "model": "uplogin.jsp",
            "CAS_LT": cas_lt,
            "service": "",
            "warn": "",
            "showCode": "1" if need_verification else "",
            "username": self.username,
            "password": self.password,
            "button": "",
        }
        if need_verification:  # Verification code required
            r = self.session.get(
                "https://passport.ustc.edu.cn/validatecode.jsp?type=login",
                verify=(not self.debug),
            )
            form_data["LT"] = recognizeBytes(r.content)
        r = self.session.post(
            url, data=form_data, allow_redirects=False, verify=(not self.debug)
        )
        return (r.status_code == 302) and (
            r.headers["location"] == "https://passport.ustc.edu.cn/success.jsp"
        )

    def service(self, serv_url: str) -> bool | str:
        """Login to service at given url. Return False if not logged in, or the final url if logged in.

        :param serv_url: The url of the service to be logged in. Either like `https://jw.ustc.edu.cn/ucas-sso/login` or `https://passport.ustc.edu.cn/login?service=https%3A%2F%2Fjw.ustc.edu.cn%2Fucas-sso%2Flogin`.
        """
        r = self.session.get(serv_url, verify=(not self.debug))
        if r.url.startswith("https://passport.ustc.edu.cn/"):
            return False
        else:
            return r.url

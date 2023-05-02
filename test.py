from typing import Optional, Union

from pydantic import BaseModel, HttpUrl, parse_obj_as, validator


class Config(BaseModel):
    url: Union[HttpUrl, str]

    @validator("url", always=True)
    def validate_url(cls, v: Union[HttpUrl, str]) -> HttpUrl:
        if isinstance(v, str):
            return parse_obj_as(HttpUrl, v)
        return v


url = "http://test_url.com"
test_config = Config(url=url)

print(test_config.url)
print(isinstance(test_config.url, HttpUrl))

test_config2 = Config(url=parse_obj_as(HttpUrl, url))
print(test_config2.url)
print(isinstance(test_config2.url, HttpUrl))
print(test_config2.url)

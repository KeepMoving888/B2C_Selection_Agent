# api/deps.py
from typing import Optional

from fastapi import Depends

from api.routers.auth import UserInfo, get_current_user


async def optional_user(user: Optional[UserInfo] = Depends(get_current_user)) -> Optional[UserInfo]:
    return user

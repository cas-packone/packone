import json
import urllib
import httplib2
from collections import defaultdict

from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login
from django.conf import settings
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db import transaction


def _do_post(host, url, args={}):
    '''
    发送POST请求
    '''
    args = urllib.parse.urlencode(args)
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
    conn = httplib2.HTTPSConnectionWithTimeout(host)
    conn.request('POST', url, args, headers)

    res = conn.getresponse()
    if res.status == 200:
        data = json.loads(res.read().decode())
        return data
    return False

def escience_callback(request):
    """
    平台科技网回调接口
    登录回调操作：（带code参数）
        1、根据code获取第三方账户用户信息，根据用户信息查找与之绑定的平台用户或者创建对应的用户
        2、设置用户登录
        3、跳转到首页
    """
    if settings.DEBUG: print('平台科技网回调接口')
    code = request.GET.get('code', None)
    if code:
        args = {
            "client_id": settings.ESCIENCE_APP_KEY,
            "client_secret": settings.ESCIENCE_APP_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": settings.ESCIENCE_CALLBACK,
            "code":code
        }
        
        data = _do_post(settings.ESCIENCE_LOGIN_HOST, settings.ESCIENCE_TOKEN_URL, args)

        escience_login_success = False
        user_data = defaultdict(lambda:None)
        if data and 'userInfo' in data:
            try:
                for k, v in json.loads(data.get('userInfo')).items():
                    user_data[k] = v
            except Exception as e:
                import traceback
                traceback.print_exc()
                print('[CSNET ERROR]', data.get('userInfo'), e)
            if user_data['cstnetIdStatus'] == 'active':
                escience_login_success = True

        if escience_login_success:
            user = None

            # 根据科技网邮箱查找用户
            user_objs = User.objects.filter(email=user_data["cstnetId"])            
            if user_objs.exists():
                user = user_objs.first()

            # 科技网账户和科技网邮箱都没有绑定，则注册新用户
            if user is None:
                user, created = User.objects.get_or_create(username=user_data['cstnetId'],
                        email=user_data['cstnetId'], last_name=user_data['truename'], is_staff=True)

                # 注册失败，报错
                if not created:
                    raise Exception("login fail!")

            # 登录
            if user:
                auth_login(request, user)
                return HttpResponseRedirect(reverse('scispace_index'))
    return HttpResponseRedirect(reverse('scispace_login'))

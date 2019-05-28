def get_space(request):
    parts=request.get_full_path().split('/')
    if len(parts)>2 and parts[1]=='space':
        return parts[2]
    return None
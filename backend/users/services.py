from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken


def revoke_all_refresh_tokens(user):
    """Make every refresh token of this user unusable (log out everywhere)."""
    already = BlacklistedToken.objects.filter(token__user=user).values_list("token_id", flat=True)
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=token) for token in OutstandingToken.objects.filter(user=user).exclude(id__in=already)]
    )

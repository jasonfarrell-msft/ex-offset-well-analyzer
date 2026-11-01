using System.Net;
using System.Security.Cryptography;
using System.Text;
using DrillAdvisor.Api.Limits;

namespace DrillAdvisor.Web.Limits;

/// <summary>
/// Hashes the remote address already normalized by forwarded-header middleware.
/// </summary>
public sealed class RemoteIpSourceIdentifier : IClientSourceIdentifier
{
    private readonly byte[] _salt = RandomNumberGenerator.GetBytes(32);

    /// <inheritdoc />
    public string GetSourceKey(HttpRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);

        var address = request.HttpContext.Connection.RemoteIpAddress
            ?? IPAddress.None;
        var addressBytes = Encoding.UTF8.GetBytes(address.ToString());
        var input = new byte[_salt.Length + addressBytes.Length];
        Buffer.BlockCopy(_salt, 0, input, 0, _salt.Length);
        Buffer.BlockCopy(addressBytes, 0, input, _salt.Length, addressBytes.Length);
        return Convert.ToHexString(SHA256.HashData(input));
    }
}

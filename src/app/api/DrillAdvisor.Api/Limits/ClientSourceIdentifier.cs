using System.Net;
using System.Security.Cryptography;
using System.Text;
using Microsoft.AspNetCore.Http;

namespace DrillAdvisor.Api.Limits;

/// <summary>
/// Produces a nonreversible process-local source key without logging the address.
/// </summary>
public interface IClientSourceIdentifier
{
    /// <summary>
    /// Gets a stable process-local key for the request source.
    /// </summary>
    string GetSourceKey(HttpRequest request);
}

/// <summary>
/// Hashes the trusted forwarded source address using a process-random salt.
/// </summary>
public sealed class ClientSourceIdentifier : IClientSourceIdentifier
{
    private readonly byte[] _salt = RandomNumberGenerator.GetBytes(32);

    /// <inheritdoc />
    public string GetSourceKey(HttpRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);

        var address = GetForwardedAddress(request)
            ?? request.HttpContext.Connection.RemoteIpAddress
            ?? IPAddress.None;
        var addressBytes = Encoding.UTF8.GetBytes(address.ToString());
        var input = new byte[_salt.Length + addressBytes.Length];
        Buffer.BlockCopy(_salt, 0, input, 0, _salt.Length);
        Buffer.BlockCopy(addressBytes, 0, input, _salt.Length, addressBytes.Length);
        return Convert.ToHexString(SHA256.HashData(input));
    }

    private static IPAddress? GetForwardedAddress(HttpRequest request)
    {
        var forwarded = request.Headers["X-Forwarded-For"].ToString();
        if (string.IsNullOrWhiteSpace(forwarded))
        {
            return null;
        }

        var candidate = forwarded.Split(',', 2, StringSplitOptions.TrimEntries)[0];
        return IPAddress.TryParse(candidate, out var address) ? address : null;
    }
}

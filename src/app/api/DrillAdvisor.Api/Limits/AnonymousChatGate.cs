using DrillAdvisor.Api.Configuration;
using Microsoft.Extensions.Options;

namespace DrillAdvisor.Api.Limits;

/// <summary>
/// Applies deterministic fixed-instance anonymous chat controls.
/// </summary>
public interface IAnonymousChatGate
{
    /// <summary>
    /// Attempts to admit a Foundry chat call for the supplied source key.
    /// </summary>
    ChatAdmission TryAcquire(string sourceKey);
}

/// <summary>
/// Represents an admission decision and its optional concurrency lease.
/// </summary>
public sealed record ChatAdmission(
    bool IsAllowed,
    int StatusCode,
    string Code,
    int RetryAfterSeconds,
    IDisposable? Lease)
{
    /// <summary>
    /// Creates an allowed decision.
    /// </summary>
    public static ChatAdmission Allowed(IDisposable lease) =>
        new(true, 200, string.Empty, 0, lease);
}

/// <summary>
/// Uses rolling in-memory windows and UTC-day accounting for one fixed instance.
/// </summary>
public sealed class AnonymousChatGate(
    IOptions<PublicChatOptions> options,
    TimeProvider timeProvider) : IAnonymousChatGate
{
    private static readonly TimeSpan AdmissionWindow = TimeSpan.FromMinutes(1);
    private readonly object _sync = new();
    private readonly PublicChatOptions _options =
        options?.Value ?? throw new ArgumentNullException(nameof(options));
    private readonly TimeProvider _timeProvider =
        timeProvider ?? throw new ArgumentNullException(nameof(timeProvider));
    private readonly Queue<DateTimeOffset> _globalAdmissions = new();
    private readonly Dictionary<string, SourceState> _sources =
        new(StringComparer.Ordinal);
    private DateOnly _dailyDate;
    private int _dailyFoundryCalls;
    private int _globalConcurrency;

    /// <inheritdoc />
    public ChatAdmission TryAcquire(string sourceKey)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(sourceKey);

        lock (_sync)
        {
            if (!_options.Enabled)
            {
                return new(false, 503, "public_chat_disabled", 60, null);
            }

            var now = _timeProvider.GetUtcNow();
            ResetDailyCounter(now);
            RemoveExpired(_globalAdmissions, now);
            RemoveExpiredSources(now);

            if (!_sources.TryGetValue(sourceKey, out var source))
            {
                source = new SourceState();
                _sources.Add(sourceKey, source);
            }

            RemoveExpired(source.Admissions, now);

            if (_dailyFoundryCalls >= _options.DailyFoundryCalls)
            {
                var nextDay = now.UtcDateTime.Date.AddDays(1);
                return new(
                    false,
                    503,
                    "daily_foundry_limit_reached",
                    Math.Max(1, Convert.ToInt32(Math.Ceiling((nextDay - now.UtcDateTime).TotalSeconds))),
                    null);
            }

            if (source.Admissions.Count >= _options.PerSourcePerMinute)
            {
                return new(
                    false,
                    429,
                    "source_rate_limit_reached",
                    RetryAfter(source.Admissions.Peek(), now),
                    null);
            }

            if (_globalAdmissions.Count >= _options.GlobalPerMinute)
            {
                return new(
                    false,
                    429,
                    "global_rate_limit_reached",
                    RetryAfter(_globalAdmissions.Peek(), now),
                    null);
            }

            if (source.Concurrency >= _options.PerSourceConcurrency)
            {
                return new(false, 429, "source_concurrency_limit_reached", 1, null);
            }

            if (_globalConcurrency >= _options.GlobalConcurrency)
            {
                return new(false, 503, "global_concurrency_limit_reached", 1, null);
            }

            source.Admissions.Enqueue(now);
            _globalAdmissions.Enqueue(now);
            source.Concurrency++;
            _globalConcurrency++;
            _dailyFoundryCalls++;
            return ChatAdmission.Allowed(new AdmissionLease(this, sourceKey));
        }
    }

    private void Release(string sourceKey)
    {
        lock (_sync)
        {
            if (_sources.TryGetValue(sourceKey, out var source))
            {
                source.Concurrency = Math.Max(0, source.Concurrency - 1);
            }

            _globalConcurrency = Math.Max(0, _globalConcurrency - 1);
        }
    }

    private void ResetDailyCounter(DateTimeOffset now)
    {
        var currentDate = DateOnly.FromDateTime(now.UtcDateTime);
        if (_dailyDate == currentDate)
        {
            return;
        }

        _dailyDate = currentDate;
        _dailyFoundryCalls = 0;
    }

    private void RemoveExpiredSources(DateTimeOffset now)
    {
        foreach (var entry in _sources)
        {
            RemoveExpired(entry.Value.Admissions, now);
        }

        var emptyKeys = _sources
            .Where(entry =>
                entry.Value.Concurrency == 0
                && entry.Value.Admissions.Count == 0)
            .Select(entry => entry.Key)
            .ToArray();
        foreach (var key in emptyKeys)
        {
            _sources.Remove(key);
        }
    }

    private static void RemoveExpired(
        Queue<DateTimeOffset> admissions,
        DateTimeOffset now)
    {
        while (admissions.TryPeek(out var admittedAt)
               && now - admittedAt >= AdmissionWindow)
        {
            admissions.Dequeue();
        }
    }

    private static int RetryAfter(
        DateTimeOffset earliestAdmission,
        DateTimeOffset now) =>
        Math.Max(
            1,
            Convert.ToInt32(
                Math.Ceiling(
                    (earliestAdmission + AdmissionWindow - now).TotalSeconds)));

    private sealed class SourceState
    {
        public Queue<DateTimeOffset> Admissions { get; } = new();

        public int Concurrency { get; set; }
    }

    private sealed class AdmissionLease(
        AnonymousChatGate owner,
        string sourceKey) : IDisposable
    {
        private AnonymousChatGate? _owner = owner;

        public void Dispose()
        {
            Interlocked.Exchange(ref _owner, null)?.Release(sourceKey);
        }
    }
}

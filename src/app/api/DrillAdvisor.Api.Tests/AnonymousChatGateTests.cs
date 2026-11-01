using DrillAdvisor.Api.Configuration;
using DrillAdvisor.Api.Limits;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Options;

namespace DrillAdvisor.Api.Tests;

public sealed class AnonymousChatGateTests
{
    private static readonly DateTimeOffset Start =
        new(2026, 10, 26, 12, 0, 0, TimeSpan.Zero);

    [Fact]
    public void TryAcquire_KillSwitchDefaultsClosed()
    {
        var gate = new AnonymousChatGate(
            Options.Create(new PublicChatOptions()),
            new AdjustableTimeProvider(Start));

        var result = gate.TryAcquire("source");

        Assert.False(result.IsAllowed);
        Assert.Equal(StatusCodes.Status503ServiceUnavailable, result.StatusCode);
        Assert.Equal("public_chat_disabled", result.Code);
    }

    [Fact]
    public void TryAcquire_EnforcesPerSourceRollingMinute()
    {
        var time = new AdjustableTimeProvider(Start);
        var gate = CreateGate(time);

        for (var index = 0; index < 3; index++)
        {
            using var lease = gate.TryAcquire("source").Lease;
        }

        var blocked = gate.TryAcquire("source");
        time.Advance(TimeSpan.FromMinutes(1));
        var admitted = gate.TryAcquire("source");

        Assert.False(blocked.IsAllowed);
        Assert.Equal(StatusCodes.Status429TooManyRequests, blocked.StatusCode);
        Assert.True(admitted.IsAllowed);
        admitted.Lease?.Dispose();
    }

    [Fact]
    public void TryAcquire_EnforcesPerSourceConcurrency()
    {
        var gate = CreateGate(new AdjustableTimeProvider(Start));
        var first = gate.TryAcquire("source");

        var blocked = gate.TryAcquire("source");
        first.Lease?.Dispose();
        var admitted = gate.TryAcquire("source");

        Assert.True(first.IsAllowed);
        Assert.False(blocked.IsAllowed);
        Assert.Equal("source_concurrency_limit_reached", blocked.Code);
        Assert.True(admitted.IsAllowed);
        admitted.Lease?.Dispose();
    }

    [Fact]
    public void TryAcquire_EnforcesDailyFoundryLimit()
    {
        var options = new PublicChatOptions
        {
            Enabled = true,
            DailyFoundryCalls = 2,
        };
        var gate = new AnonymousChatGate(
            Options.Create(options),
            new AdjustableTimeProvider(Start));

        gate.TryAcquire("one").Lease?.Dispose();
        gate.TryAcquire("two").Lease?.Dispose();
        var blocked = gate.TryAcquire("three");

        Assert.False(blocked.IsAllowed);
        Assert.Equal(StatusCodes.Status503ServiceUnavailable, blocked.StatusCode);
        Assert.Equal("daily_foundry_limit_reached", blocked.Code);
    }

    private static AnonymousChatGate CreateGate(TimeProvider timeProvider) =>
        new(
            Options.Create(
                new PublicChatOptions
                {
                    Enabled = true,
                }),
            timeProvider);
}

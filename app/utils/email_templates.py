def verification_email(verification_url: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <meta name="color-scheme" content="light dark" />
  <meta name="supported-color-schemes" content="light dark" />
  <title>Verify your MoneyHana email</title>
  <style>
    :root {{
      color-scheme: light dark;
    }}

    /* Light mode (default) */
    body {{
      background-color: #f9fafb;
    }}
    .email-wrapper {{
      background-color: #f9fafb;
    }}
    .card {{
      background-color: #ffffff;
      border-color: #e5e7eb;
    }}
    .body-text {{
      color: #6b7280;
    }}
    .heading {{
      color: #111827;
    }}
    .footer-text {{
      color: #9ca3af;
    }}
    .fallback-url {{
      color: #5c5cff;
    }}
    .expiry-note {{
      color: #9ca3af;
    }}
    .expiry-highlight {{
      color: #374151;
    }}
    .fallback-label {{
      color: #6b7280;
    }}
    .logo-text {{
      color: #111827;
    }}

    /* Dark mode */
    @media (prefers-color-scheme: dark) {{
      body {{
        background-color: #0b1120 !important;
      }}
      .email-wrapper {{
        background-color: #0b1120 !important;
      }}
      .card {{
        background-color: #111827 !important;
        border-color: #1f2937 !important;
      }}
      .body-text {{
        color: #9ca3af !important;
      }}
      .heading {{
        color: #f9fafb !important;
      }}
      .footer-text {{
        color: #374151 !important;
      }}
      .expiry-note {{
        color: #6b7280 !important;
      }}
      .expiry-highlight {{
        color: #d1d5db !important;
      }}
      .fallback-label {{
        color: #4b5563 !important;
      }}
      .logo-text {{
        color: #ffffff !important;
      }}
    }}
  </style>
</head>
<body class="email-wrapper" style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" role="presentation" class="email-wrapper" style="padding:48px 16px;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;max-width:560px;">

          <!-- Logo -->
          <tr>
            <td style="padding-bottom:32px;">
              <p class="logo-text" style="margin:0;font-size:22px;font-weight:800;letter-spacing:1.5px;">
                <span style="color:#5c5cff;">MONEY</span>HANA
              </p>
            </td>
          </tr>

          <!-- Card -->
          <tr>
            <td class="card" style="border-radius:16px;border:1px solid;overflow:hidden;">

              <!-- Accent bar -->
              <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td style="height:4px;background:linear-gradient(90deg,#5c5cff,#818cf8);"></td>
                </tr>
              </table>

              <!-- Body -->
              <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td style="padding:40px 40px 32px;">

                    <!-- Icon -->
                    <table cellpadding="0" cellspacing="0" role="presentation" style="margin-bottom:28px;">
                      <tr>
                        <td style="background:#ede9fe;border-radius:12px;padding:14px;width:48px;height:48px;text-align:center;">
                          <span style="display:inline-block;font-size:20px;line-height:24px;color:#5c5cff;">✓</span>
                        </td>
                      </tr>
                    </table>

                    <h1 class="heading" style="margin:0 0 12px 0;font-size:24px;font-weight:700;line-height:1.3;">
                      Confirm your email address
                    </h1>
                    <p class="body-text" style="margin:0 0 12px 0;font-size:15px;line-height:1.7;">
                      Hi there! Thanks for signing up for MoneyHana — your personal finance dashboard for tracking spending, understanding patterns, and building smarter money habits.
                    </p>
                    <p class="body-text" style="margin:0 0 32px 0;font-size:15px;line-height:1.7;">
                      Tap the button below to verify your email and activate your account.
                    </p>

                    <!-- CTA -->
                    <table cellpadding="0" cellspacing="0" role="presentation">
                      <tr>
                        <td style="border-radius:8px;background:#5c5cff;">
                          <a href="{verification_url}"
                             style="display:inline-block;padding:14px 32px;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;letter-spacing:0.2px;">
                            Verify my email
                          </a>
                        </td>
                      </tr>
                    </table>

                    <p class="expiry-note" style="margin:24px 0 0 0;font-size:13px;line-height:1.6;">
                      This link expires in <span class="expiry-highlight" style="font-weight:500;">24 hours</span>. If you didn't create a MoneyHana account, you can safely ignore this email.
                    </p>

                  </td>
                </tr>
              </table>

              <!-- Fallback URL -->
              <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td style="padding:0 40px 32px;">
                    <p class="fallback-label" style="margin:0 0 6px 0;font-size:12px;">
                      Button not working? Copy and paste this link into your browser:
                    </p>
                    <p class="fallback-url" style="margin:0;font-size:12px;word-break:break-all;color:#5c5cff;">{verification_url}</p>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:28px 0 0 0;text-align:center;">
              <p class="footer-text" style="margin:0 0 4px 0;font-size:13px;font-weight:600;letter-spacing:0.5px;">MONEYHANA</p>
              <p class="footer-text" style="margin:0;font-size:12px;">Financial clarity without the noise.</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""


def digest_email(
    first_name: str,
    due_subscriptions: list[dict],
    trial_subscriptions: list[dict],
) -> str:
    def subscription_row(sub: dict) -> str:
        return f"""
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid #e5e7eb;">
            <p style="margin:0;font-size:14px;font-weight:600;color:#111827;">{sub['name']}</p>
            <p style="margin:4px 0 0 0;font-size:12px;color:#6b7280;">{sub['category']} · Due {sub['due_date']}</p>
          </td>
          <td style="padding:10px 0;border-bottom:1px solid #e5e7eb;text-align:right;">
            <p style="margin:0;font-size:14px;font-weight:600;color:#111827;">${sub['amount']}</p>
          </td>
        </tr>"""

    def trial_row(sub: dict) -> str:
        return f"""
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid #e5e7eb;">
            <p style="margin:0;font-size:14px;font-weight:600;color:#111827;">{sub['name']}</p>
            <p style="margin:4px 0 0 0;font-size:12px;color:#b45309;">Free trial ends {sub['trial_ends_at']} · Will auto-charge ${sub['amount']}</p>
          </td>
          <td style="padding:10px 0;border-bottom:1px solid #e5e7eb;text-align:right;">
            <p style="margin:0;font-size:14px;font-weight:600;color:#b45309;">${sub['amount']}</p>
          </td>
        </tr>"""

    due_rows = "".join(subscription_row(s) for s in due_subscriptions)
    trial_rows = "".join(trial_row(s) for s in trial_subscriptions)

    trial_section = f"""
        <p style="margin:28px 0 12px 0;font-size:13px;font-weight:600;color:#f59e0b;text-transform:uppercase;letter-spacing:0.5px;">
          Free Trials Ending This Week
        </p>
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
          {trial_rows}
        </table>
    """ if trial_subscriptions else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <meta name="color-scheme" content="light dark"/>
  <meta name="supported-color-schemes" content="light dark"/>
  <title>Your payments due this week</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{ background-color: #f9fafb; }}
    .email-wrapper {{ background-color: #f9fafb; }}
    .card {{ background-color: #ffffff; border-color: #e5e7eb; }}
    .heading {{ color: #111827; }}
    .body-text {{ color: #6b7280; }}
    .footer-text {{ color: #9ca3af; }}
    .logo-text {{ color: #111827; }}
    @media (prefers-color-scheme: dark) {{
      body {{ background-color: #0b1120 !important; }}
      .email-wrapper {{ background-color: #0b1120 !important; }}
      .card {{ background-color: #111827 !important; border-color: #1f2937 !important; }}
      .heading {{ color: #f9fafb !important; }}
      .body-text {{ color: #9ca3af !important; }}
      .footer-text {{ color: #374151 !important; }}
      .logo-text {{ color: #ffffff !important; }}
    }}
  </style>
</head>
<body class="email-wrapper" style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation" class="email-wrapper" style="padding:48px 16px;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;max-width:560px;">

          <!-- Logo -->
          <tr>
            <td style="padding-bottom:32px;">
              <p class="logo-text" style="margin:0;font-size:22px;font-weight:800;letter-spacing:1.5px;">
                <span style="color:#5c5cff;">MONEY</span>HANA
              </p>
            </td>
          </tr>

          <!-- Card -->
          <tr>
            <td class="card" style="border-radius:16px;border:1px solid;overflow:hidden;">

              <!-- Accent bar -->
              <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td style="height:4px;background:linear-gradient(90deg,#5c5cff,#818cf8);"></td>
                </tr>
              </table>

              <!-- Body -->
              <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td style="padding:40px 40px 32px;">

                    <h1 class="heading" style="margin:0 0 8px 0;font-size:22px;font-weight:700;line-height:1.3;">
                      Payments due this week
                    </h1>
                    <p class="body-text" style="margin:0 0 28px 0;font-size:15px;line-height:1.7;">
                      Hi {first_name}, here's a summary of your subscriptions due between now and next Monday.
                    </p>

                    <!-- Due this week -->
                    <p style="margin:0 0 12px 0;font-size:13px;font-weight:600;color:#5c5cff;text-transform:uppercase;letter-spacing:0.5px;">
                      Due This Week
                    </p>
                    <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                      {due_rows}
                    </table>

                    {trial_section}

                    <p class="body-text" style="margin:28px 0 0 0;font-size:13px;line-height:1.6;">
                      Log in to MoneyHana to confirm payments and keep your expenses up to date.
                    </p>

                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:28px 0 0 0;text-align:center;">
              <p class="footer-text" style="margin:0 0 4px 0;font-size:13px;font-weight:600;letter-spacing:0.5px;">MONEYHANA</p>
              <p class="footer-text" style="margin:0;font-size:12px;">Financial clarity without the noise.</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
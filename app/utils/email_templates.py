def verification_email(verification_url: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background-color:#0b1020;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0b1020;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:12px;border:1px solid #1e293b;overflow:hidden;">
          
          <!-- Header -->
          <tr>
            <td style="padding:28px 32px;background:#020617;border-bottom:1px solid #1e293b;">
              <span style="color:#3b82f6;font-weight:700;font-size:20px;letter-spacing:1px;">MONEYHANA</span>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 32px;color:#e2e8f0;">
              <h1 style="margin:0 0 14px 0;font-size:22px;color:#f8fafc;">Welcome to MoneyHana 👋</h1>
              <p style="margin:0 0 18px 0;color:#94a3b8;font-size:15px;line-height:1.6;">
                Your financial dashboard is ready. MoneyHana helps you track spending,
                understand patterns, and build smarter money habits.
              </p>
              <p style="margin:0 0 24px 0;color:#94a3b8;font-size:15px;line-height:1.6;">
                Before getting started, please confirm your email address.
              </p>

              <!-- CTA Button -->
              <table cellpadding="0" cellspacing="0" style="margin:30px 0;">
                <tr>
                  <td align="center" style="background:#2563eb;border-radius:8px;">
                    <a href="{verification_url}" style="display:inline-block;padding:14px 26px;color:#ffffff;text-decoration:none;font-weight:600;font-size:14px;">
                      Verify Your Email
                    </a>
                  </td>
                </tr>
              </table>

              <p style="margin-top:20px;color:#64748b;font-size:13px;">
                If the button above doesn't work, copy and paste this link into your browser:
              </p>
              <p style="word-break:break-all;color:#3b82f6;font-size:13px;">{verification_url}</p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:24px 32px;background:#020617;border-top:1px solid #1e293b;color:#64748b;font-size:12px;">
              MoneyHana<br>Financial clarity without the noise.
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
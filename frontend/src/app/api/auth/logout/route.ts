import { NextRequest, NextResponse } from "next/server";

export const GET = async (req: NextRequest) => {
  // Get Auth0 configuration from environment variables
  const auth0Domain =
    process.env.AUTH0_ISSUER_BASE_URL?.replace("https://", "") ||
    process.env.AUTH0_DOMAIN;
  const auth0ClientId = process.env.AUTH0_CLIENT_ID;
  const auth0BaseUrl = process.env.AUTH0_BASE_URL;

  if (!auth0Domain || !auth0ClientId || !auth0BaseUrl) {
    return NextResponse.json(
      { error: "Auth0 configuration missing" },
      { status: 500 }
    );
  }

  // Redirect to Auth0 logout
  const logoutUrl = new URL(`https://${auth0Domain}/v2/logout`);
  logoutUrl.searchParams.set("client_id", auth0ClientId);
  logoutUrl.searchParams.set("returnTo", auth0BaseUrl);

  return NextResponse.redirect(logoutUrl.toString());
};

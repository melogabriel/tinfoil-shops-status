def post_to_bluesky(results):
    if not BLUESKY_HANDLE or not BLUESKY_PASSWORD:
        print("Bluesky credentials missing from environment variables. Skipping post.")
        return

    total = len(results)
    online = sum(1 for _, status in results if "✅" in status)
    issues = sum(1 for _, status in results if "⚠️" in status)
    offline = sum(1 for _, status in results if "❌" in status)

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    timestamp = now.strftime('%H:%M %Z')

    # --- 1. BUILD MAIN SCOREBOARD POST ---
    main_tb = client_utils.TextBuilder()
    main_tb.text(f"🎮 Tinfoil Shop Status Update ({timestamp})\n\n")
    main_tb.text(f"🟢 Online: {online}/{total}\n")
    main_tb.text(f"🟡 Issues/Maint: {issues}\n")
    main_tb.text(f"🔴 Offline: {offline}\n\n")
    main_tb.text("#NintendoSwitch #Tinfoil")

    try:
        client = Client()
        client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)
        
        # Send main post
        root_post = client.send_post(main_tb)
        print("Successfully posted main summary to Bluesky!")
        
        # Keep track of the thread parent
        parent_reference = {
            'cid': root_post.cid,
            'uri': root_post.uri
        }
        root_reference = parent_reference.copy()

        # --- 2. CHUNKED REPLIES FOR DIRECTORY ---
        current_reply_tb = client_utils.TextBuilder()
        current_reply_tb.text("📋 Current Shop Directory:\n\n")
        
        # Approximate safety counter for characters (Max 300, chunking around ~240)
        current_length = len(current_reply_tb.build_text())

        for host, status in results:
            icon = "❌"
            if "✅" in status:
                icon = "🟢"
            elif "⚠️" in status:
                icon = "🟡"

            # Build this shop's line representation
            line_tb = client_utils.TextBuilder()
            line_tb.text(f"{icon} {host} — ")
            
            link_url = None
            for custom_key, custom_url in CUSTOM_SHOP_LINKS.items():
                if custom_key in host:
                    link_url = custom_url
                    break
            
            if link_url:
                line_tb.link("[Access]", link_url)
            else:
                line_tb.link("[Link]", f"https://{host}")
            line_tb.text("\n")

            # Calculate if adding this line would exceed our character chunk limit
            line_text_len = len(line_tb.build_text())
            
            if current_length + line_text_len > 250:
                # Post the full chunk before starting a new one
                reply_post = client.send_post(
                    current_reply_tb,
                    reply_to={'root': root_reference, 'parent': parent_reference}
                )
                print("Posted directory chunk reply!")
                
                # Update parent to chain the replies sequentially
                parent_reference = {'cid': reply_post.cid, 'uri': reply_post.uri}
                
                # Start a completely fresh chunk
                current_reply_tb = client_utils.TextBuilder()
                current_reply_tb.text("📋 Directory Continued:\n\n")
                current_length = len(current_reply_tb.build_text())

            # Append the validated shop line to the active builder
            current_reply_tb.add(line_tb)
            current_length += line_text_len

        # Post the very last remaining chunk if it contains shops
        if current_length > len("📋 Directory Continued:\n\n") and current_length > len("📋 Current Shop Directory:\n\n"):
            client.send_post(
                current_reply_tb,
                reply_to={'root': root_reference, 'parent': parent_reference}
            )
            print("Posted final directory chunk reply!")

    except Exception as e:
        print(f"Failed to post to Bluesky: {e}")

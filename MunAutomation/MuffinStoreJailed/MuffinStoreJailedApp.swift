//
//  MuffinStoreJailedApp.swift
//  MuffinStoreJailed
//
//  Created by Mineek on 31/12/2024.
//

import SwiftUI
import UniformTypeIdentifiers

var pipe = Pipe()
var sema = DispatchSemaphore(value: 0)
var weOnADebugBuild: Bool = false

@main
struct MuffinStoreJailedApp: App {
    @StateObject private var appData = AppData.shared
    
    @AppStorage("autoCleanApp") var autoCleanApp: Bool = true
    
    init() {
        // Setup log stuff (redirect stdout)
        setvbuf(stdout, nil, _IONBF, 0)
        dup2(pipe.fileHandleForWriting.fileDescriptor, STDOUT_FILENO)
        #if DEBUG
        weOnADebugBuild = true
        #else
        weOnADebugBuild = false
        #endif
    }
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appData)
                .onAppear {
                    if autoCleanApp {
                        cleanUp()
                    }
                }
                // receive the incoming url
                .onOpenURL { schemedURL in
                    let rawURL = schemedURL.absoluteString.replacingOccurrences(of: "pancakestore:", with: "")
                    if let appLink = rawURL.removingPercentEncoding {
                        appData.appLink = appLink
                        print("Successfully received app link! \(appLink)")
                    }
                }
        }
    }
}

extension String: @retroactive Error {}

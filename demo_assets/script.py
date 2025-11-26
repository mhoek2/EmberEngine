class MyScript:
    value       : int = export(1)
      
    """Default script template"""
    def onStart( self ) -> None:
        self.camera = self.scene.getCamera()
        #print('onStart()')
        pass

    def onEnable( self ):
        #print('onEnable()')
        pass

    def onDisable( self ):
        #print('onDisable()')
        pass
        
    def onUpdate( self ) -> None:
        # print exported value for debugging purposes
        #print(self.value)
 
        keypress = self.key.get_pressed()
        velocity = self.value

        if keypress[pygame.K_u]:
            self.gameObject.setActive(False)
    
        if keypress[pygame.K_LCTRL] or keypress[pygame.K_RCTRL]:
            velocity *= 10

        move = self.renderer.deltaTime * velocity

        if keypress[pygame.K_w]:
            self.transform.local_position[2] += move
            self.camera.transform.local_position[2] += move
        if keypress[pygame.K_s]:
            self.transform.local_position[2] -= move
            self.camera.transform.local_position[2] -= move
        if keypress[pygame.K_d]:
            self.transform.local_position[0] -= move
            self.camera.transform.local_position[0] -= move
        if keypress[pygame.K_a]:
            self.transform.local_position[0] += move
            self.camera.transform.local_position[0] += move